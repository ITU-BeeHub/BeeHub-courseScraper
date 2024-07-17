import os
import requests
import datetime
import json
from copy import deepcopy

from github import pushChanges
from bs4 import BeautifulSoup

base_url = "https://www.sis.itu.edu.tr/TR/ogrenci/ders-programi/ders-programi.php?seviye=LS"

date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def fetchCoursePage(course_code: str) -> list[dict[str:str]]:
    url = f"{base_url}&derskodu={course_code}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the div with the class "table-responsive"
    table = soup.find("div", class_="table-responsive")
    
    # Convert table to json format with corresponding headers
    courses = []
    headers = []
    course = {}

    for i, row in enumerate(table.find_all("tr")):
        if i == 0: # skip Turkish headers
            continue
        elif i == 1: # get English headers
            headers = [str(cell.text).strip() for cell in row.find_all(["td", "th"])]
        else: # get course info
            for idx, cell in enumerate(row.find_all(["td", "th"])):
                course[headers[idx]] = str(cell.get_text()).strip()
            courses.append(deepcopy(course))
            course.clear()

    return courses

def fetchCourses() -> list[str]:
    # Send GET request to the specified URL    
    response = requests.get(base_url)

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract course codes from the option elements
    course_codes = [option["value"] for option in soup.find_all("option") if len(option["value"]) == 3]

    return course_codes



if __name__ == "__main__":
    course_codes = fetchCourses()

    # Create a folder with the name of today's date and hour inside public folder
    os.mkdir(os.path.join(repo_root_dir, "public", date))

    for course_code in course_codes:

        # Fetch the course page
        course = fetchCoursePage(course_code)

        # Write the course page to a file
        file_path = os.path.join(repo_root_dir, "public", date, f"{course_code}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(course, file, ensure_ascii=False)


    # Update most_recent.txt file
    with open(os.path.join(repo_root_dir, "public", "most_recent.txt"), "w", encoding="utf-8") as file:
        file.write(date)

    # Update the course_codes.json file
    with open(os.path.join(repo_root_dir, "public", "course_codes.json"), "w", encoding="utf-8") as file:
        json.dump(course_codes, file, ensure_ascii=False)

    pushChanges(repo_root_dir, f"Add course schedules for {date}")
