# Legal Assistant
_Example project using the Exa Python SDK_

---


## What This Document Covers
- Using pymupdf to convert a PDF file to text
- Generating a batch of search queries for Exa using an LLM
- Retrieving relevant URLs with Exa


### Requirements
- **Exa API Key**: Allows you to perform Exa searches.
- **Anthropic API Key**: Enables the use of language models for query creation.

> **Note:** Get 1,000 Exa searches per month free just for signing up!

Happy searching!

---

## Setup

First, make sure you have the relevant packages installed.

```bash
# Open terminal and install with pip
pip install exa_py
pip install anthropic
pip install pymupdf
pip install python-dotenv
```

Create a directory for your project. In this directory, you should have your Python file, the PDF you would like to analyze and a .env file. It should be structured like this:

```bash
project/
├── legal_assistant.py
├── epic_v_apple.pdf    #this should be your pdf file
├── .env
```

Next, add your API keys to your .env file. This allows you to share your Python file with others while keeping our API keys seperate and secret.

```bash
EXA_API_KEY='YOUR API KEY HERE'
ANTHROPIC_API_KEY='YOUR API KEY HERE'
```

Now it's time to set up your Python file. Import the Exa and Anthropic SDKs and set up your API keys to create client objects for each. You will also need to import pymupdf (for reading the PDF), and os and dotenv (for retrieving API keys).

```python
import pymupdf
from exa_py import Exa
import anthropic
#if using a .env file to store your API keys, include the below imports
import os
from dotenv import load_dotenv
```

Then, institiate your clients with your API keys. In this example, we are using load_dotenv( ) to get our API keys from a .env file within our project directory.
```python
load_dotenv()   #loads API keys from .env file
exa_api_key = os.getenv("EXA_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
exa = Exa(exa_api_key)
client = anthropic.Anthropic(api_key=anthropic_api_key)
```
For the last piece of setup, you should:
* Creating a Python list of specific details you want your LLM to create queries for
* Create a variable to store the name of a .txt file you will be creating
* Create a variable to store the name of the PDF we want to analyze

```python
details_to_extract = [
    'Parties involved (Plaintiff, and Defendant)',
    'Legal standards and case law (this is very important, you can find referenced cases because they have a \"v.\" in their title)', 
    'Presiding judges previous rulings (rulings on similar cases, recent cases)',
    'Legal standards applied (interpretation of standards in previous rulings)',
    'Analysis (Likelihood of Success on the Merits, Irreparable Harm, Balance of Equities, Public Interest)'
]
TXT_FILE = "output.txt" #name for a text file you will be creating
PDF_NAME = "epic_v_apple.pdf"   #name of pdf file you are reading, the file should be in your project directory
```

Ok, great! Now you are ready to start writing some helper functions!

---

### Writing functions for turning a PDF into a .txt file

You'll first want to use [pymupdf](https://pymupdf.readthedocs.io/en/latest/the-basics.html) to convert your pdf file into a .txt file. Then, you will need to read that .txt file into Python as a string.

You should write two functions to do this:
- pdf_to_txt(PDF, NAME, TXT_FILE)
- txt_to_str(TXT_FILE)

```python
def pdf_to_txt(PDF_NAME, TXT_FILE):
    doc = pymupdf.open(PDF_NAME) # open a document
    out = open(TXT_FILE, "wb") # create a text output
    for page in doc: # iterate the document pages
        pdf_text = page.get_text().encode("utf8") # get plain text (is in UTF-8)
        out.write(pdf_text) # write text of page
        out.write(bytes((12,))) # write page delimiter (form feed 0x0C)
    out.close()


def txt_to_str(TXT_FILE):
    text_string = ""
    # Read text from a .txt file
    with open(TXT_FILE, "r", encoding="utf-8") as file:
        for line in file:
            # Strip whitespace and check if the line contains only digits
            if not line.strip().isdigit():
                text_string += line  # Concatenate the line to text if it has non-digit content

    return text_string

```

> **Note:** You may notice that txt_to_str(TXT_FILE) reads the .txt file line by line and checks if the line is just a number. This is because legal filings typically have line numbers. Giving your LLM lines with just number markings can confuse it and be costly. Especially when analyzing large documents.

---

### Prompting your LLM with text from the PDF

Now that you have functions to convert your PDF into a string, the next step is to create a function that sends this string to an LLM, prompting it to generate Exa queries.

Before writing this function, it is important for you to understand the best prompt practices for your LLM of choice and for Exa. If you would like to see some best practices for using the Anthropic API for legal analysis, you can review [this example use case](https://docs.anthropic.com/en/docs/about-claude/use-case-guides/legal-summarization). Exa works best with [prompts](https://docs.exa.ai/reference/prompting-guide) that:

* Are Phrased as Statements: "Here's a great article about X:" works better than "What is X?
* End with a Colon: Many effective prompts end with ":", mimicking natural link sharing.

In the following function, you will prompt Claude to return queries that follow these prompting practices. You will also prompt Claude to return the queries in a particular structure (seperated by new line characters), ensuring that you will get consistant output that can be parsed efficiently.

```python
def summarize_document(text, details_to_extract, model="claude-3-5-sonnet-20241022", max_tokens=1000):

    # Format the details to extract to be placed within the prompt's context
    details_to_extract_str = '\n'.join(details_to_extract)
    
    # Prompt the model to summarize the sublease agreement
    prompt = f"""Generate google search queries that will tell us more about the background of this court filing. The queries should be formatted as article titles. Focus on these key aspects:

    {details_to_extract_str}

    Provide queries in the form of potential article titles, end each article title with a :, seperat titles by new line characters, do not include categories, each query should be on its own line with no blank lines. For example:

    
    query1: 
    query2: 
    query3: 
    etc.
    
    You should only output this list.

    If any information is not explicitly stated in the document that you think is important, please generate a potential article title that would help us find out more information.

    Court filing text:
    {text}
    """

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system="You are a legal analyst specializing in corporate case law. You are to generate the names of internet articles that will produce background on the filing.",
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "<summary>"}
        ],
        stop_sequences=["</summary>"]
    )

    return response.content[0].text

```
---

### Executing Multiple Exa API Calls

Your final function will take a string of queries and a delimiter as arguments, execute Exa API calls for each query, and return a list of the responses. In this example, `delimiter='\n'`, as we asked Claude to separate queries with a newline.

Because you are using specificly tailored queries generated by Claude, you will want to set `use_autoprompt=False`. Claude will also generate many different types of queries, so it will be best for you to set `type="auto"`.

```python
def batch_exa_search(search_string, delimiter='\n'):
    combined_results = []
    # Split the string into individual queries
    queries = search_string.split(delimiter)
    
    for query in queries:
        
        if not query.isspace():
            # Perform a search
            results = exa.search(
                query,
                num_results=3,
                use_autoprompt=False,
                type="auto",
                
            )
            combined_results.append(results)
    
    
    return combined_results
```
---

### Putting It All Together

Now, let's combine all the functions we've written so that they can be executed when the program runs. Given a PDF, these functions will analyze the court filing PDF, generate search queries and feed those queries to Exa. Three simple steps!

```python
if __name__ == "__main__":
    load_dotenv()
    exa_api_key = os.getenv("EXA_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    exa = Exa(exa_api_key)
    client = anthropic.Anthropic(api_key=anthropic_api_key)

    details_to_extract = [
        'Parties involved (Plaintiff, and Defendant)',
        'Legal standards and case law (this is very important, you can find referenced cases because they have a \"v.\" in their title)', 
        'Presiding judges previous rulings (rulings on similar cases, recent cases)',
        'Legal standards applied (interpretation of standards in previous rulings)',
        'Analysis (Likelihood of Success on the Merits, Irreparable Harm, Balance of Equities, Public Interest)'
    ]

    TXT_FILE = "output.txt"
    PDF_NAME = "epic_v_apple.pdf"   #change this to the name of your PDF


    pdf_to_txt(PDF_NAME, TXT_FILE)
    document_text = txt_to_str(TXT_FILE)


    document_queries = summarize_document(document_text, details_to_extract)

    batch_results = batch_exa_search(document_queries)

    # Process results
    print("\nShowing Results:")
    for result in batch_results:
        for item in result.results:
                print(f"- {item.title}: {item.url}")


```

This Python implementation of Exa demonstrates how to leverage Exa's Auto Search feature and the Anthropic API to create an automated legal assistant tool. By combining Exa's powerful search capabilities with Claude-3.5 Sonnet's language understanding and generation, we've created a system that can quickly synthesize and gather information from a given PDF.
