from websearch import WebSearch as web
import requests
from bs4 import BeautifulSoup
from langchain_openai import OpenAI

llm = OpenAI()
locations = ["chicago", "atlanta", "new york"]  # list of major locations in the midwest to use


def search(location):  # this function contains our search parameters and outputs a list of urls
    search_results = []
    for page in web(
            location + "\"Asian\" \"pageant\" \"2024\" -site:linkedin.com -site:tiktok.com "
                       "-site:threads.net -site:google.com -site:facebook.com -site:instagram.com "
                       "-site:maps.google.com -site:reddit.com"
            # large sites like facebook must be excluded because these are very hostile towards scraping
    ).pages[:2]:  # this variable controls how many urls are given per location; can be adjusted to scale
        search_results.append(page)
    return search_results  # Return the collected search results as a list


def clean_html(html):  # this function cleans our inputted html by removing leading spaces, blank lines, and the tags
    soup = BeautifulSoup(html, "html.parser")
    for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside"]):
        script_or_style.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text


for location in locations:  # main control flow
    URLs = search(location)  # returns a list of X urls per each major MidWest Location
    for URL in URLs:  # for each one of these url in this new list
        ScrapedContent = requests.get(URL).text  # scrape the url using requests.get(URL).text
        WebContent = clean_html(ScrapedContent)  # tidy it with our HTML cleaning function
        response = llm.invoke("""Analyze the provided webpage text to identify the main or most significant event 
        mentioned. Extract and summarize detailed information about this event, including its location, date,  
        city/state. We are specifically looking for Pageants, Galas, Fairs, Fundraisers and other such 
        community/heritage based events related to AAPI or other ethnic groups. If certain details are not explicitly 
        mentioned, use context clues to provide a comprehensive understanding. Present the information in a 
        structured format, and indicate 'N/A' for any details that cannot be determined. Also add a description with 
        anything cool/fun/noteworthy you think should be added to the database, at the end; examples of things to 
        include in the description are, what type of event it is, as well as perhaps any estimation of size/scale but 
        you have some freedom here. Your goal is to work as INFO EXTRACTION GPT! Good job! Include the information in 
        EXACTLY this format:

        Name of Event: 
        Date: mm/dd/yyyy  (might be a range of dates) 
        Location: City, State 
        Description: (limit to 850 char)

        Here is the Web info(Don't include this back in the response): """ + WebContent)
        # give openai API our cleaned html with an extraction prompt
        print(URL)
        print(response)  # print the llm's response in the desired name/date/location/description format
