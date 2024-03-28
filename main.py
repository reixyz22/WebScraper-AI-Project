from websearch import WebSearch as web
import requests
from bs4 import BeautifulSoup
from langchain_openai import OpenAI
import pandas as pd


excel_path = "ChiAWEMIDWESTDatabase.xlsx"
df = pd.DataFrame(columns=["URL", "Name of Event", "Date", "Location", "Description"])

llm = OpenAI()
locations = [  # list of major locations in the midwest to use
    "Illinois", "Chicago", "Springfield", "Peoria",
    "Indiana", "Indianapolis", "Fort Wayne", "Bloomington",
    "Iowa", "Des Moines", "Cedar Rapids", "Iowa City",
    "Kansas", "Wichita", "Topeka", "Kansas City",
    "Michigan", "Detroit", "Grand Rapids", "Ann Arbor",
    "Minnesota", "Minneapolis", "Saint Paul", "Duluth",
    "Missouri", "Kansas City", "St. Louis", "Springfield",
    "Nebraska", "Omaha", "Lincoln", "Grand Island", "Fargo",
    "Ohio", "Columbus", "Cleveland", "Cincinnati",
    "South Dakota", "Sioux Falls", "Rapid City", "Pierre",
    "Wisconsin", "Milwaukee", "Madison", "Green Bay"
]
prompt: str = """Analyze the provided webpage text to identify the main or most significant event 
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
        Date: Month date, year  (might be a range of dates) 
        Location: City, State 
        Description: (limit to 850 char)

        Here is the Web info (Don't include this back in the response): """


def search(location):  # this function contains our search parameters and outputs a list of urls
    search_results = []
    for page in web(
            location + "\"Asian\" \"pageant\" \"2024\"  -site:linkedin.com -site:tiktok.com "
                       "-site:threads.net -site:google.com -site:facebook.com -site:instagram.com "
            # large sites like facebook must be excluded because these are very hostile towards scrape
    ).pages[:2]:  # this variable controls how many urls are given per location; can be adjusted to scale
        if not page.startswith("https://maps.google.com"):  # weird but important edge case
            search_results.append(page)
    return search_results  # Return the collected search results as a list


def clean_html(html):  # this takes raw html and makes it into something more readable
    soup = BeautifulSoup(html, "html.parser")
    #  this makes sure to get meta tags, such as the description found on chi-awe's website
    description = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={
        'property': 'og:description'})
    meta_description = description['content'] if description else 'No description found.'
    # this removes trailing/leading spaces, line breaks, and all html tags
    for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside"]):
        script_or_style.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
    combined_text = meta_description + "\n\n" + cleaned_text
    return combined_text


response = " "
for location in locations:  # main control flow
    URLs = search(location)  # returns a list of X urls per each major MidWest Location
    for URL in URLs:  # for each one of these url in this new list
        ScrapedContent = requests.get(URL).text  # scrape the url using requests.get(URL).text
        WebContent = clean_html(ScrapedContent)  # tidy it with our HTML cleaning function
        try:  # sometimes we get weird ratelimit bugs, so we have to try/Exception to fix these
            response = llm.invoke(prompt + WebContent)  # give openai API our cleaned html with an extraction prompt
            info = response  # obtain the llm's response in the desired name/date/location/description format

            lines2 = info.strip().split("\n")  # split the llm response into datapoints
            info_name = lines2[0].split(":", 1)[1].strip()
            info_date = lines2[1].split(":", 1)[1].strip()
            info_location = lines2[2].split(":", 1)[1].strip()
            info_description = lines2[3].split(":", 1)[1].strip()

            new_event = pd.DataFrame({  # Create a new DataFrame to hold this event's information
                "URL": [URL],
                "Name of Event": [info_name],
                "Date": [info_date],
                "Location": [info_location],
                "Description": [info_description]
            })
            if info_date in df['Date'].values:
                # duplicate prevention, done by date but also should prevent duplicated events in general
                print(f"An event on {info_date} is already in the database. Skipping addition.")
                continue
            df = pd.concat([df, new_event], ignore_index=True)  # Append the new event data to the existing DataFrame
        except Exception as e:  # Handle potential errors and skip to the next URL
            print(f"An error occurred for {URL}: {e}")
            print(response)
            continue
df.to_excel(excel_path, index=False, engine='openpyxl')  # Save the DataFrame to the Excel file outside the loop
print(f"All new data saved to {excel_path}")
