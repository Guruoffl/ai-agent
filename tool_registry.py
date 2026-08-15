from tools import (
    calculator,
    get_time,
    web_search,
    read_webpage,
    save_memory,
    search_memory
)


tool_registry = {

    "calculator":
        calculator,

    "get_time":
        get_time,

    "web_search":
        web_search,

    "read_webpage":
        read_webpage,

    "save_memory":
        save_memory,

    "search_memory":
        search_memory

}


tools = [

    {
        "type": "function",

        "function": {

            "name":
                "calculator",

            "description":
                "Perform basic arithmetic calculations.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "a": {
                        "type": "number"
                    },

                    "b": {
                        "type": "number"
                    },

                    "operation": {

                        "type":
                            "string",

                        "enum": [
                            "add",
                            "subtract",
                            "multiply",
                            "divide"
                        ]

                    }

                },

                "required": [
                    "a",
                    "b",
                    "operation"
                ]

            }

        }

    },


    {
        "type": "function",

        "function": {

            "name":
                "get_time",

            "description":
                "Get the current real-world date and time in India (IST).",

            "parameters": {

                "type":
                    "object",

                "properties": {},

                "required": []

            }

        }

    },


    {
        "type": "function",

        "function": {

            "name":
                "web_search",

            "description":
                "Search the internet using Google for current or factual information.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "query": {

                        "type":
                            "string",

                        "description":
                            "The search query."

                    }

                },

                "required": [
                    "query"
                ]

            }

        }

    },


    {
        "type": "function",

        "function": {

            "name":
                "read_webpage",

            "description":
                "Read and extract text from a webpage.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "url": {

                        "type":
                            "string",

                        "description":
                            "The complete webpage URL."

                    }

                },

                "required": [
                    "url"
                ]

            }

        }

    },


    {
        "type": "function",

        "function": {

            "name":
                "save_memory",

            "description":
                "Save durable and useful information for future conversations. Do not save passwords, API keys, secrets, or sensitive information.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "content": {

                        "type":
                            "string",

                        "description":
                            "The information to remember."

                    }

                },

                "required": [
                    "content"
                ]

            }

        }

    },


    {
        "type": "function",

        "function": {

            "name":
                "search_memory",

            "description":
                "Search long-term memory using semantic similarity.",

            "parameters": {

                "type":
                    "object",

                "properties": {

                    "query": {

                        "type":
                            "string",

                        "description":
                            "The information to search for."

                    }

                },

                "required": [
                    "query"
                ]

            }

        }

    }

]