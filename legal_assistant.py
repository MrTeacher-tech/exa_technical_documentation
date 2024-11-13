import pymupdf
from exa_py import Exa
import anthropic
import os
import datetime
#if using a .env file, include the below import
from dotenv import load_dotenv


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




def queries_from_document(text, details_to_extract, model="claude-3-5-sonnet-20241022", max_tokens=1000):

    # Format the details to extract to be placed within the prompt's context
    details_to_extract_str = '\n'.join(details_to_extract)
    
    # Prompt the model to generate queries
    prompt = f"""Generate google search queries that will tell us more about the background of this court filing. The queries should be formatted as article titles. Focus on these key aspects:

    {details_to_extract_str}

    Provide queries in the form of potential article titles, seperated by new line characters, do not include categories, each query should be on its own line with no blank lines. For example:

    
    query1 
    query2 
    query3 
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

def batch_exa_search(search_string, delimiter='\n'):
    combined_results = []
    # Split the string into individual queries
    queries = search_string.split(delimiter)
    
    for query in queries:
        
        if not query.isspace():
            # Perform a search
            results = exa.search(
                query,
                num_results=5,
                use_autoprompt=False,
                type="auto",
                
            )
            combined_results.append(results)
    
    
    
    return combined_results


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


    document_queries = queries_from_document(document_text, details_to_extract)

    batch_results = batch_exa_search(document_queries)

    # Process results
    print("\nShowing Results:")
    for result in batch_results:
        for item in result.results:
                print(f"- {item.title}: {item.url}")

