import os
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from bs4 import BeautifulSoup

from memory import remember, search_memories


load_dotenv()


# -----------------------------
# Calculator
# -----------------------------

def calculator(a, b, operation):

    if operation == "add":
        return a + b

    elif operation == "subtract":
        return a - b

    elif operation == "multiply":
        return a * b

    elif operation == "divide":

        if b == 0:
            return "Cannot divide by zero"

        return a / b

    else:
        return "Unknown operation"


# -----------------------------
# Current Time
# -----------------------------

def get_time():

    india_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    return india_time.strftime(
        "%Y-%m-%d %I:%M:%S %p IST"
    )


# -----------------------------
# Web Search
# -----------------------------

def web_search(query):

    api_key = os.getenv(
        "SERPAPI_API_KEY"
    )

    if not api_key:
        return (
            "SERPAPI_API_KEY is not configured."
        )

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key
    }

    response = requests.get(
        "https://serpapi.com/search.json",
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    results = []

    for result in data.get(
        "organic_results",
        []
    )[:5]:

        results.append({

            "title":
                result.get("title"),

            "link":
                result.get("link"),

            "snippet":
                result.get("snippet")

        })


    if not results:

        return "No search results found."


    return results


# -----------------------------
# Read Webpage
# -----------------------------

def read_webpage(url):

    try:

        response = requests.get(

            url,

            headers={
                "User-Agent":
                    (
                        "Mozilla/5.0 "
                        "(Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    )
            },

            timeout=15
        )

        response.raise_for_status()


        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        for element in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside"
        ]):

            element.decompose()


        text = soup.get_text(
            separator=" ",
            strip=True
        )


        text = text[:12000]


        if not text:

            return (
                "Could not extract readable text."
            )


        return text


    except Exception as e:

        return (
            f"Failed to read webpage: {str(e)}"
        )


# -----------------------------
# Save Long-Term Memory
# -----------------------------

def save_memory(content):

    return remember(content)


# -----------------------------
# Search Long-Term Memory
# -----------------------------

def search_memory(query):

    return search_memories(query)