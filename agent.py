import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from openai import OpenAI
from json_repair import repair_json
from tool_registry import tool_registry, tools
load_dotenv()
client = OpenAI(
    base_url=
        "https://openrouter.ai/api/v1",
    api_key=
        os.getenv(
            "OPENROUTER_API_KEY"
        )
)
MAX_USER_TURNS = 10
MAX_PLAN_STEPS = 5
MAX_STEP_RETRIES = 2
MAX_EXECUTION_CYCLES = 8
def get_current_date():
    india_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )
    return india_time.strftime(
        "%Y-%m-%d"
    )
SYSTEM_MESSAGE = {
    "role":
        "system",
    "content":
        """
You are a helpful AI agent.
Available tools:
calculator
get_time
web_search
read_webpage
save_memory
search_memory
Use tools when appropriate.
Never invent tool results.
Never claim real-time information is unavailable
when an appropriate tool is available.
Use relevant long-term memory when it helps.
"""
}
MEMORY_MANAGER_PROMPT = """

You are a long-term memory classifier.

Determine whether the user's message contains
durable personal information worth remembering.

SAVE:

"I am learning Python."

"I am learning Python and its frameworks."

"My goal is to become an AI engineer."

"I prefer Python."

"I am building an AI project."

DO NOT SAVE:

"What should I learn next?"

"What is Python?"

"How do I learn Python?"

"Which framework should I learn?"

"What time is it?"

"Calculate 25 * 4."

If a message contains both a personal fact and a question,
save the personal fact but continue answering the question.

Example:

"I am learning Python. What should I learn next?"

Return:

{
    "should_remember": true,
    "memory": "User is learning Python.",
    "is_memory_only": false
}

For:

"I am learning Python."

Return:

{
    "should_remember": true,
    "memory": "User is learning Python.",
    "is_memory_only": true
}

For:

"What should I learn next?"

Return:

{
    "should_remember": false,
    "memory": "",
    "is_memory_only": false
}

Return ONLY valid JSON.
"""

PLANNER_PROMPT = """

You are the planning component of an AI agent.

Create the minimum number of steps required to complete
the user's request.

Available tools:

calculator:
Perform arithmetic.

get_time:
Get the current time in India.

web_search:
Search the internet for current information.

read_webpage:
Read a webpage.

search_memory:
Search long-term memory.

IMPORTANT:

The current date will be provided separately.

Never use an outdated year such as 2024 unless the user
specifically asks about 2024.

Use the current year for searches about:
- latest
- current
- recent
- today
- this year
- current trends
- current technologies

Use relevant memory.

Do not ask unnecessary clarification questions.

Do not create steps that wait for the user.

Do not create steps asking the user to respond.

For simple questions, use one step.

Maximum 5 steps.

Return ONLY valid JSON.

Format:

{
    "plan": [
        {
            "step": 1,
            "description": "..."
        }
    ]
}
"""


EVALUATOR_PROMPT = """

You are the evaluator of an AI agent.

Determine whether the original task has been completed.

If the available result is enough to answer the user,
return done=true.

If another INTERNAL action is required,
return done=false.

Never create a step that waits for the user.

Never create a step that asks the user to respond.

Return ONLY valid JSON.
"""


def parse_json(text):

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError:

        repaired = repair_json(
            text
        )

        return json.loads(
            repaired
        )



def evaluate_memory(user_input):

    try:

        response = client.chat.completions.create(

            model="openrouter/free",

            messages=[

                {
                    "role":
                        "system",

                    "content":
                        MEMORY_MANAGER_PROMPT
                },

                {
                    "role":
                        "user",

                    "content":
                        user_input
                }

            ]

        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:

            return {

                "should_remember":
                    False,

                "memory":
                    "",

                "is_memory_only":
                    False

            }

        decision = parse_json(
            content
        )

        if not isinstance(
            decision,
            dict
        ):

            raise ValueError(
                "Invalid memory response"
            )

        memory = str(
            decision.get(
                "memory",
                ""
            )
        ).strip()

        should_remember = bool(
            decision.get(
                "should_remember",
                False
            )
        )

        is_memory_only = bool(
            decision.get(
                "is_memory_only",
                False
            )
        )

        if not memory:

            should_remember = False
            is_memory_only = False

        return {

            "should_remember":
                should_remember,

            "memory":
                memory,

            "is_memory_only":
                is_memory_only

        }

    except Exception as e:

        print(
            f"[Memory manager skipped: {e}]"
        )

        return {

            "should_remember":
                False,

            "memory":
                "",

            "is_memory_only":
                False

        }

def save_important_memory(memory):

    try:

        save_tool = tool_registry[
            "save_memory"
        ]

        save_tool(
            content=memory
        )

        print(
            f"[Memory saved: {memory}]"
        )

        return True

    except Exception as e:

        print(
            f"[Could not save memory: {e}]"
        )

        return False



def retrieve_memories(user_input):

    try:

        search_tool = tool_registry[
            "search_memory"
        ]

        results = search_tool(
            query=user_input
        )

        if not isinstance(
            results,
            list
        ):

            return []

        return results

    except Exception as e:

        print(
            f"[Memory search skipped: {e}]"
        )

        return []



def format_memory_context(memories):

    if not memories:

        return (
            "No relevant long-term memory was found."
        )

    lines = []

    for memory in memories:

        lines.append(

            f"- {memory['content']} "
            f"(similarity: "
            f"{memory['score']:.2f})"

        )

    return "\n".join(lines)



def create_plan(
    user_input,
    memory_context
):

    current_date = get_current_date()

    planner_input = f"""

Current date:

{current_date}

User request:

{user_input}

Relevant long-term memory:

{memory_context}

Use the memory when relevant.

If the user asks about current information,
use the current date above when constructing
web searches.
"""

    response = client.chat.completions.create(

        model="openrouter/free",

        messages=[

            {
                "role":
                    "system",

                "content":
                    PLANNER_PROMPT
            },

            {
                "role":
                    "user",

                "content":
                    planner_input
            }

        ]

    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    try:

        data = parse_json(
            content
        )

        plan = data.get(
            "plan",
            []
        )

        valid_plan = []

        for item in plan:

            if not isinstance(
                item,
                dict
            ):

                continue

            description = item.get(
                "description"
            )

            if not description:

                continue

            valid_plan.append({

                "step":
                    len(valid_plan) + 1,

                "description":
                    description

            })

        if valid_plan:

            return valid_plan[
                :MAX_PLAN_STEPS
            ]

    except Exception as e:

        print(
            f"[Planner JSON error: {e}]"
        )

    return [{

        "step":
            1,

        "description":
            user_input

    }]


def parse_arguments(arguments):

    try:

        return json.loads(
            arguments
        )

    except json.JSONDecodeError:

        repaired = repair_json(
            arguments
        )

        return json.loads(
            repaired
        )


def execute_tool(tool_call):

    tool_name = (
        tool_call
        .function
        .name
    )

    arguments = parse_arguments(
        tool_call
        .function
        .arguments
    )

    print(
        f"[Using tool: {tool_name}]"
    )

    if tool_name not in tool_registry:

        return {

            "status":
                "failed",

            "tool":
                tool_name,

            "error":
                "Tool not found."

        }

    try:

        result = tool_registry[
            tool_name
        ](
            **arguments
        )


        if isinstance(
            result,
            str
        ):

            failure_markers = [

                "not configured",

                "failed",

                "error",

                "could not",

                "cannot"

            ]

            lowered = result.lower()

            if any(
                marker in lowered
                for marker in failure_markers
            ):

                return {

                    "status":
                        "failed",

                    "tool":
                        tool_name,

                    "error":
                        result

                }

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
                str(e)

        }



def execute_step(
    step_description,
    previous_results,
    memory_context
):

    response = client.chat.completions.create(

        model="openrouter/free",

        messages=[

            SYSTEM_MESSAGE,

            {
                "role":
                    "user",

                "content":
                    f"""

Execute this step:

{step_description}

Relevant memory:

{memory_context}

Previous results:

{json.dumps(
    previous_results,
    indent=2
)}

Use the appropriate tool.

Do not invent results.
"""
            }

        ],

        tools=tools

    )

    message = (
        response
        .choices[0]
        .message
    )

    if not message.tool_calls:

        return {

            "status":
                "success",

            "result":
                message.content,

            "tool":
                None

        }

    results = []

    for tool_call in message.tool_calls:

        result = execute_tool(
            tool_call
        )

        results.append(
            result
        )

    failed = any(

        result.get(
            "status"
        ) == "failed"

        for result in results

    )

    if failed:

        return {

            "status":
                "failed",

            "result":
                results,

            "tool":
                None

        }

    return {

        "status":
            "success",

        "result":
            results,

        "tool":
            results[0].get(
                "tool"
            )

    }



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

Original request:

{user_input}

Execution results:

{json.dumps(
    results,
    indent=2
)}
"""
            }

        ]

    )

    try:

        data = parse_json(
            response
            .choices[0]
            .message
            .content
        )

        return data

    except Exception:

        return {

            "done":
                True,

            "reason":
                "Returning available results.",

            "next_step":
                ""

        }



def generate_final_answer(
    user_input,
    results,
    memory_context
):

    response = client.chat.completions.create(

        model="openrouter/free",

        messages=[

            SYSTEM_MESSAGE,

            {
                "role":
                    "user",

                "content":
                    f"""

Answer this user request:

{user_input}

Relevant memory:

{memory_context}

Execution results:

{json.dumps(
    results,
    indent=2
)}

If a tool failed, do not pretend that
the tool succeeded.

Give the most useful answer possible.
"""
            }

        ]

    )

    return (
        response
        .choices[0]
        .message
        .content
    )



while True:

    user_input = input(
        "\nYou: "
    )

    if user_input.lower() == "exit":

        print(
            "Agent stopped."
        )

        break


    print(
        "\n[Checking long-term memory...]"
    )

    memory_decision = evaluate_memory(
        user_input
    )

    if memory_decision[
        "should_remember"
    ]:

        save_important_memory(
            memory_decision[
                "memory"
            ]
        )

    if memory_decision[
        "is_memory_only"
    ]:

        print(
            "\n[Memory statement detected. "
            "Skipping planner.]"
        )

        print(
            "\nAgent: Got it. "
            "I'll remember that."
        )

        continue

    print(
        "\n[Searching long-term memory...]"
    )

    memories = retrieve_memories(
        user_input
    )

    memory_context = (
        format_memory_context(
            memories
        )
    )

    if memories:

        print(
            "[Relevant memories found:]"
        )

        for memory in memories:

            print(

                f"- {memory['content']} "
                f"(score: "
                f"{memory['score']:.2f})"

            )

    else:

        print(
            "[No relevant memories found.]"
        )


    print(
        "\n[Creating plan...]"
    )

    plan = create_plan(

        user_input,

        memory_context

    )

    print(
        "\n[Plan]"
    )

    for step in plan:

        print(

            f"{step['step']}. "
            f"{step['description']}"

        )

    print(
        "\n[Executing agent...]"
    )

    execution_results = []

    for step in plan:

        print(
            f"\n[Step {step['step']}] "
            f"{step['description']}"
        )

        result = execute_step(

            step["description"],

            execution_results,

            memory_context

        )

        execution_results.append({

            "step":
                step["step"],

            "description":
                step["description"],

            "status":
                result["status"],

            "tool":
                result.get(
                    "tool"
                ),

            "result":
                result.get(
                    "result",
                    result.get(
                        "error"
                    )
                )

        })

        print(

            f"[Step status: "
            f"{result['status']}]"

        )

        if result["status"] == "failed":

            print(

                f"[Tool failed: "
                f"{result.get('error', result.get('result'))}]"

            )


    print(
        "\n[Evaluating progress...]"
    )

    evaluation = evaluate_progress(

        user_input,

        execution_results

    )

    print(
        f"[Done: "
        f"{evaluation.get('done', True)}]"
    )

    print(
        f"[Reason: "
        f"{evaluation.get('reason', '')}]"
    )


    print(
        "\n[Generating final answer...]"
    )

    answer = generate_final_answer(

        user_input,

        execution_results,

        memory_context

    )

    print(
        "\nAgent:",
        answer
    )