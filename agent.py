import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from json_repair import repair_json

from tool_registry import tool_registry, tools


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_USER_TURNS = 10
MAX_PLAN_STEPS = 5
MAX_STEP_RETRIES = 2
MAX_EXECUTION_CYCLES = 8


# ============================================================
# SYSTEM MESSAGE
# ============================================================

SYSTEM_MESSAGE = {
    "role": "system",
    "content": """
You are a helpful AI agent.

You have access to several tools.

Use calculator for arithmetic.

Use get_time for the current time.

Use web_search when the user needs current
or web-based information.

Use read_webpage when you need to inspect
the contents of a webpage.

Use search_memory when previous long-term
information may be relevant.

Use save_memory when the user tells you
something durable that will be useful later.

Good things to remember include:

- preferences
- learning goals
- projects
- skills
- long-term plans

Do not save:

- passwords
- API keys
- secrets
- sensitive personal information
- temporary conversation details

When calling a tool, provide valid JSON
arguments that exactly match the tool schema.

Use tool results instead of inventing facts.
"""
}


# ============================================================
# PLANNER PROMPT
# ============================================================

PLANNER_PROMPT = """
You are the planning component of an AI agent.

Analyze the user's task and break it into
logical sequential steps.

Create only the steps that are actually
necessary.

For simple questions, create one step.

For complex tasks, create multiple steps.

Never create more than 5 initial steps.

Return ONLY valid JSON.

Format:

{
    "plan": [
        {
            "step": 1,
            "description": "..."
        },
        {
            "step": 2,
            "description": "..."
        }
    ]
}

Do not execute tools.
Only create the plan.
"""


# ============================================================
# EVALUATOR PROMPT
# ============================================================

EVALUATOR_PROMPT = """
You are the evaluation component of an AI agent.

Your job is to determine whether the user's
original request has been sufficiently completed.

Look at:

1. The original request
2. The completed plan steps
3. Their results
4. Any failed steps

If enough reliable information exists to answer
the user, mark the task as done.

If more work is genuinely required, mark it as
not done and provide ONE specific next step.

Do not repeat an already completed step unless
there is a clear reason to retry it.

Return ONLY valid JSON.

If complete:

{
    "done": true,
    "reason": "The task has been completed."
}

If more work is required:

{
    "done": false,
    "reason": "Why more work is required.",
    "next_step": "The next action that should be performed."
}
"""


# ============================================================
# CONVERSATION MEMORY
# ============================================================

messages = [
    SYSTEM_MESSAGE
]


# ============================================================
# GET MESSAGE ROLE
# ============================================================

def get_role(message):

    if isinstance(message, dict):
        return message.get("role")

    return message.role


# ============================================================
# TRIM SHORT-TERM MEMORY
# ============================================================

def trim_memory():

    global messages

    user_positions = []

    for index, message in enumerate(messages):

        if get_role(message) == "user":
            user_positions.append(index)

    if len(user_positions) <= MAX_USER_TURNS:
        return

    first_kept_position = user_positions[
        -MAX_USER_TURNS
    ]

    messages = [
        SYSTEM_MESSAGE
    ] + messages[first_kept_position:]


# ============================================================
# SAFE JSON PARSER
# ============================================================

def parse_json(text):

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        repaired = repair_json(text)

        return json.loads(repaired)


# ============================================================
# PARSE TOOL ARGUMENTS
# ============================================================

def parse_arguments(arguments):

    try:

        return json.loads(arguments)

    except json.JSONDecodeError:

        print(
            "[Warning: repairing malformed JSON...]"
        )

        repaired = repair_json(arguments)

        return json.loads(repaired)


# ============================================================
# VALIDATE PLAN
# ============================================================

def validate_plan(
    plan,
    user_input
):

    if not isinstance(plan, list):

        return [
            {
                "step": 1,
                "description": user_input
            }
        ]

    valid_steps = []

    for item in plan:

        if not isinstance(item, dict):
            continue

        description = item.get("description")

        if not isinstance(description, str):
            continue

        description = description.strip()

        if not description:
            continue

        valid_steps.append({

            "step":
                len(valid_steps) + 1,

            "description":
                description

        })

        if len(valid_steps) >= MAX_PLAN_STEPS:
            break

    if not valid_steps:

        return [
            {
                "step": 1,
                "description": user_input
            }
        ]

    return valid_steps


# ============================================================
# CREATE INITIAL PLAN
# ============================================================

def create_plan(user_input):

    response = client.chat.completions.create(

        model="openrouter/free",

        messages=[
            {
                "role": "system",
                "content": PLANNER_PROMPT
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    content = response.choices[0].message.content

    try:

        plan_data = parse_json(content)

        raw_plan = plan_data.get(
            "plan",
            []
        )

        return validate_plan(
            raw_plan,
            user_input
        )

    except Exception:

        print(
            "[Planner failed. "
            "Using original request as one step.]"
        )

        return [
            {
                "step": 1,
                "description": user_input
            }
        ]


# ============================================================
# EXECUTE TOOL
# ============================================================

def execute_tool(tool_call):

    tool_name = tool_call.function.name

    raw_arguments = tool_call.function.arguments

    print(
        f"[Using tool: {tool_name}]"
    )

    # --------------------------------------------------------
    # Parse arguments
    # --------------------------------------------------------

    try:

        arguments = parse_arguments(
            raw_arguments
        )

    except Exception as e:

        return {

            "status":
                "failed",

            "tool":
                tool_name,

            "error":
                (
                    "Could not parse tool arguments: "
                    f"{str(e)}"
                )

        }

    # --------------------------------------------------------
    # Find tool
    # --------------------------------------------------------

    tool = tool_registry.get(
        tool_name
    )

    if tool is None:

        return {

            "status":
                "failed",

            "tool":
                tool_name,

            "error":
                (
                    f"Tool '{tool_name}' "
                    f"does not exist."
                )

        }

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    try:

        result = tool(
            **arguments
        )

        return {

            "status":
                "success",

            "tool":
                tool_name,

            "result":
                result

        }

    except Exception as e:

        return {

            "status":
                "failed",

            "tool":
                tool_name,

            "error":
                (
                    "Tool execution error: "
                    f"{str(e)}"
                )

        }


# ============================================================
# EXECUTE ONE STEP
# ============================================================

def execute_step(
    step_description,
    previous_results
):

    step_messages = [

        SYSTEM_MESSAGE,

        {
            "role":
                "user",

            "content":
                f"""
Execute this specific step of a larger task:

{step_description}

Previous step results:

{json.dumps(
    previous_results,
    indent=2
)}

Use an appropriate tool if necessary.

If you successfully use a tool, do not
unnecessarily call the same tool again.

Return the result of this step.
"""
        }

    ]

    retry_count = 0

    while retry_count <= MAX_STEP_RETRIES:

        try:

            response = client.chat.completions.create(

                model="openrouter/free",

                messages=step_messages,

                tools=tools

            )

            message = response.choices[0].message

            # ------------------------------------------------
            # No tool required
            # ------------------------------------------------

            if not message.tool_calls:

                return {

                    "status":
                        "success",

                    "result":
                        message.content,

                    "tool":
                        None

                }

            # ------------------------------------------------
            # Execute requested tools
            # ------------------------------------------------

            tool_results = []

            for tool_call in message.tool_calls:

                tool_result = execute_tool(
                    tool_call
                )

                tool_results.append(
                    tool_result
                )

            # ------------------------------------------------
            # Check whether any tool failed
            # ------------------------------------------------

            failed = any(

                isinstance(
                    result,
                    dict
                )

                and

                result.get(
                    "status"
                ) == "failed"

                for result in tool_results

            )

            # ------------------------------------------------
            # Recovery
            # ------------------------------------------------

            if failed:

                retry_count += 1

                if retry_count > MAX_STEP_RETRIES:

                    return {

                        "status":
                            "failed",

                        "result":
                            tool_results,

                        "tool":
                            None

                    }

                print(

                    f"[Retrying step "
                    f"{retry_count}/"
                    f"{MAX_STEP_RETRIES}]"

                )

                step_messages.append(
                    message
                )

                for tool_call, result in zip(
                    message.tool_calls,
                    tool_results
                ):

                    step_messages.append({

                        "role":
                            "tool",

                        "tool_call_id":
                            tool_call.id,

                        "content":
                            json.dumps(
                                result
                            )

                    })

                step_messages.append({

                    "role":
                        "user",

                    "content":
                        """
The previous tool execution failed.

Try a different reasonable approach.

Do not repeat the exact same failed action.
"""

                })

                continue

            # ------------------------------------------------
            # Successful tool execution
            # ------------------------------------------------

            return {

                "status":
                    "success",

                "result":
                    tool_results,

                "tool":
                    (
                        tool_results[0].get(
                            "tool"
                        )
                        if tool_results
                        and isinstance(
                            tool_results[0],
                            dict
                        )
                        else None
                    )

            }

        except Exception as e:

            retry_count += 1

            if retry_count > MAX_STEP_RETRIES:

                return {

                    "status":
                        "failed",

                    "result":
                        str(e),

                    "tool":
                        None

                }

            print(

                f"[Step error. "
                f"Retrying {retry_count}/"
                f"{MAX_STEP_RETRIES}]"

            )

    return {

        "status":
            "failed",

        "result":
            "Step could not be completed.",

        "tool":
            None

    }


# ============================================================
# EVALUATE PROGRESS
# ============================================================

def evaluate_progress(
    user_input,
    results
):

    response = client.chat.completions.create(

        model="openrouter/free",

        messages=[

            {
                "role":
                    "system",

                "content":
                    EVALUATOR_PROMPT

            },

            {
                "role":
                    "user",

                "content":
                    f"""
Original user request:

{user_input}

Completed execution results:

{json.dumps(
    results,
    indent=2
)}

Determine whether the task is complete.
"""
            }

        ]

    )

    content = response.choices[0].message.content

    try:

        evaluation = parse_json(
            content
        )

        # ----------------------------------------------
        # Validate evaluator output
        # ----------------------------------------------

        if not isinstance(
            evaluation,
            dict
        ):

            return {

                "done":
                    False,

                "reason":
                    "Invalid evaluator output.",

                "next_step":
                    user_input

            }

        done = evaluation.get(
            "done",
            False
        )

        reason = evaluation.get(
            "reason",
            ""
        )

        next_step = evaluation.get(
            "next_step",
            ""
        )

        return {

            "done":
                bool(done),

            "reason":
                reason,

            "next_step":
                next_step

        }

    except Exception:

        return {

            "done":
                False,

            "reason":
                "Could not evaluate progress.",

            "next_step":
                user_input

        }


# ============================================================
# EXTRACT SIMPLE RESULT
# ============================================================

def extract_simple_result(
    step_result
):

    if not isinstance(
        step_result,
        dict
    ):

        return None

    if step_result.get(
        "status"
    ) != "success":

        return None

    result = step_result.get(
        "result"
    )

    if not isinstance(
        result,
        list
    ):

        return None

    if len(result) != 1:
        return None

    tool_result = result[0]

    if not isinstance(
        tool_result,
        dict
    ):

        return None

    if tool_result.get(
        "status"
    ) != "success":

        return None

    return tool_result.get(
        "result"
    )


# ============================================================
# GENERATE FINAL ANSWER
# ============================================================

def generate_final_answer(
    user_input,
    results
):

    # --------------------------------------------------------
    # Direct deterministic result
    # --------------------------------------------------------

    if len(results) == 1:

        simple_result = extract_simple_result(
            results[0]
        )

        if simple_result is not None:

            if results[0].get(
                "tool"
            ) == "calculator":

                return str(
                    simple_result
                )

    # --------------------------------------------------------
    # LLM final answer
    # --------------------------------------------------------

    final_messages = [

        {
            "role":
                "system",

            "content":
                """
You are the final answer component.

Answer the user's original question using
ONLY the execution results.

Do not invent facts.

Do not discuss internal planning.

Do not mention tool status.

Do not output unrelated categories.

Give the actual answer directly.

If the execution results are incomplete,
say so honestly.
"""
        },

        {
            "role":
                "user",

            "content":
                f"""
Original user request:

{user_input}

Execution results:

{json.dumps(
    results,
    indent=2
)}

Provide the final answer.
"""
        }

    ]

    response = client.chat.completions.create(

        model="openrouter/free",

        messages=final_messages

    )

    return response.choices[0].message.content


# ============================================================
# MAIN AGENT LOOP
# ============================================================

while True:

    user_input = input(
        "\nYou: "
    )

    if user_input.lower() == "exit":

        print(
            "Agent stopped."
        )

        break

    # ========================================================
    # INITIAL PLAN
    # ========================================================

    print(
        "\n[Creating plan...]"
    )

    plan = create_plan(
        user_input
    )

    print(
        "\n[Plan]"
    )

    for step in plan:

        print(
            f"{step['step']}. "
            f"{step['description']}"
        )

    # ========================================================
    # AGENT EXECUTION LOOP
    # ========================================================

    print(
        "\n[Executing agent...]"
    )

    execution_results = []

    current_step_number = 1

    current_step_description = (
        plan[0]["description"]
    )

    cycle = 0

    while cycle < MAX_EXECUTION_CYCLES:

        cycle += 1

        print(
            f"\n[Cycle {cycle}/"
            f"{MAX_EXECUTION_CYCLES}]"
        )

        print(
            f"[Step {current_step_number}] "
            f"{current_step_description}"
        )

        # ----------------------------------------------------
        # Execute
        # ----------------------------------------------------

        result = execute_step(

            step_description=
                current_step_description,

            previous_results=
                execution_results

        )

        step_record = {

            "step":
                current_step_number,

            "description":
                current_step_description,

            "status":
                result.get(
                    "status",
                    "unknown"
                ),

            "tool":
                result.get(
                    "tool"
                ),

            "result":
                result.get(
                    "result",
                    result
                )

        }

        execution_results.append(
            step_record
        )

        print(
            f"[Step status: "
            f"{step_record['status']}]"
        )

        # ----------------------------------------------------
        # Evaluate
        # ----------------------------------------------------

        print(
            "[Evaluating progress...]"
        )

        evaluation = evaluate_progress(

            user_input=
                user_input,

            results=
                execution_results

        )

        print(
            f"[Done: "
            f"{evaluation.get('done')}]"
        )

        print(
            f"[Reason: "
            f"{evaluation.get('reason', '')}]"
        )

        # ----------------------------------------------------
        # Task completed
        # ----------------------------------------------------

        if evaluation.get(
            "done"
        ):

            print(
                "\n[Agent decided the task "
                "is complete.]"
            )

            break

        # ----------------------------------------------------
        # Get next step
        # ----------------------------------------------------

        next_step = evaluation.get(
            "next_step"
        )

        if not isinstance(
            next_step,
            str
        ):

            next_step = ""

        next_step = next_step.strip()

        if not next_step:

            print(
                "[Evaluator did not provide "
                "a next step.]"
            )

            break

        current_step_number += 1

        current_step_description = (
            next_step
        )

        print(
            f"[Next step: "
            f"{current_step_description}]"
        )

    # ========================================================
    # MAX CYCLES REACHED
    # ========================================================

    if cycle >= MAX_EXECUTION_CYCLES:

        print(
            "\n[Maximum execution cycles reached.]"
        )

    # ========================================================
    # FINAL ANSWER
    # ========================================================

    print(
        "\n[Generating final answer...]"
    )

    answer = generate_final_answer(

        user_input=
            user_input,

        results=
            execution_results

    )

    print(
        "\nAgent:",
        answer
    )

    # ========================================================
    # SAVE CONVERSATION
    # ========================================================

    messages.append({

        "role":
            "user",

        "content":
            user_input

    })

    messages.append({

        "role":
            "assistant",

        "content":
            answer

    })

    trim_memory()