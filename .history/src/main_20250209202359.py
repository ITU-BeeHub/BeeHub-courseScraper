import os
import requests
import datetime
import json
from copy import deepcopy

from github import pushChanges
from bs4 import BeautifulSoup

BASE_URL = "https://obs.itu.edu.tr/public/DersProgram"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.100 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}",
    "Accept": "application/json"
}

date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROGRAM_LEVELS = ["LS", "LU", "LUI", "OL"]


# Function to get course codes based on program level
def get_course_codes(program_seviye):
    url = f"{BASE_URL}/SearchBransKoduByProgramSeviye"
    params = {"programSeviyeTipiAnahtari": program_seviye}
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve course codes: {response.status_code}")
        return []
    
# Function to get courses by code
def get_courses(program_seviye, ders_brans_kodu_id):
    url = f"{BASE_URL}/DersProgramSearch"
    data = {
        "ProgramSeviyeTipiAnahtari": program_seviye,
        "dersBransKoduId": ders_brans_kodu_id,
        "__RequestVerificationToken": "<your_verification_token_here>"
    }
    response = requests.get(url, headers=HEADERS, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve courses: {response.status_code}")
        return []


# Example Usage
if __name__ == "__main__":

    # Create a folder with the name of today's date and hour inside public folder
    os.mkdir(os.path.join(repo_root_dir, "public", date))

    # Step 1: Get course codes
    for program_seviye in PROGRAM_LEVELS:
        course_codes = get_course_codes(program_seviye)

        # Step 2: For each course code, get courses and save to file
        for code in course_codes:
            ders_brans_kodu_id = code['bransKoduId']
            course_code = code['dersBransKodu']
            courses = get_courses(program_seviye, ders_brans_kodu_id)
            if courses:

                # i know this isnt the best way to do this but i am too lazy to fix it
                # graduate and undergraduate courses can have the same course code.
                # If the course code is already in the list, we should append the courses to the existing list
                # so, i just read the file and append the new courses to the existing data
                
                # Write the course page to a file
                file_path = os.path.join(repo_root_dir, "public", date, f"{course_code}.json")
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        existing_data = json.load(file)
                except FileNotFoundError:
                    existing_data = {}

                # Append the new courses to the existing data
                for course in courses:
                    course_id = course['dersId']
                    existing_data[course_id] = course
                    
                
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(existing_data, file, ensure_ascii=False)

    # Update most_recent.txt file
    with open(os.path.join(repo_root_dir, "public", "most_recent.txt"), "w", encoding="utf-8") as file:
        file.write(date)

    # Update the course_codes.json file
    with open(os.path.join(repo_root_dir, "public", "course_codes.json"), "w", encoding="utf-8") as file:
        json.dump(course_codes, file, ensure_ascii=False)

    #pushChanges(repo_root_dir, f"Add course schedules for {date}")

