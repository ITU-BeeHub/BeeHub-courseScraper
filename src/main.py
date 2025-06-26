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


def parse_courses_html(html_content):
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='dersProgramContainer')
    if not table:
        return []

    courses_list = []
    tbody = table.find('tbody')
    if not tbody:
        return []
        
    rows = tbody.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if not cols or len(cols) < 15:
            continue

        def get_text(element):
            return element.get_text(strip=True)

        crn = get_text(cols[0])
        course_code_anchor = cols[1].find('a')
        course_code = get_text(course_code_anchor) if course_code_anchor else get_text(cols[1])
        course_title = get_text(cols[2])
        teaching_method = get_text(cols[3])
        instructor = get_text(cols[4])
        capacity = get_text(cols[9])
        enrolled = get_text(cols[10])
        reservation = get_text(cols[11])
        
        major_restriction_anchor = cols[12].find('a')
        major_restriction = get_text(major_restriction_anchor) if major_restriction_anchor else get_text(cols[12])

        prereq_anchor = cols[13].find('a')
        prerequisites = f"https://obs.itu.edu.tr{prereq_anchor['href']}" if prereq_anchor and prereq_anchor.has_attr('href') else get_text(cols[13])

        credit_class_resc = get_text(cols[14])

        schedules = []
        
        def get_parts(element):
            return [s.strip() for s in element.get_text(separator='\n').strip().split('\n') if s.strip()]

        buildings = get_parts(cols[5])
        days = get_parts(cols[6])
        times = get_parts(cols[7])
        rooms = get_parts(cols[8])

        max_len = max(len(buildings), len(days), len(times), len(rooms))
        
        buildings.extend([''] * (max_len - len(buildings)))
        days.extend([''] * (max_len - len(days)))
        times.extend([''] * (max_len - len(times)))
        rooms.extend([''] * (max_len - len(rooms)))

        for i in range(max_len):
            schedules.append({
                'building': buildings[i],
                'day': days[i],
                'time': times[i],
                'room': rooms[i]
            })

        course_data = {
            'crn': crn,
            'course_code': course_code,
            'course_title': course_title,
            'teaching_method': teaching_method,
            'instructor': instructor,
            'schedules': schedules,
            'capacity': capacity,
            'enrolled': enrolled,
            'reservation': reservation,
            'major_restriction': major_restriction,
            'prerequisites': prerequisites,
            'credit_class_resc': credit_class_resc
        }
        courses_list.append(course_data)
    
    return courses_list


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
    params = {
        "ProgramSeviyeTipiAnahtari": program_seviye,
        "dersBransKoduId": ders_brans_kodu_id,
    }
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve courses: {response.status_code}")
        return None


# Example Usage
if __name__ == "__main__":
    # Step 1: Get course codes for Graduate level
    program_seviye = "LS"  # Replace with the appropriate level code
    course_codes = get_course_codes(program_seviye)

    # Create a folder with the name of today's date and hour inside public folder
    os.mkdir(os.path.join(repo_root_dir, "public", date))

    # Step 2: For each course code, get courses and save to file
    for code in course_codes:
        ders_brans_kodu_id = code['bransKoduId']
        course_code = code['dersBransKodu']
        html_content = get_courses(program_seviye, ders_brans_kodu_id)
        
        if html_content:
            courses = parse_courses_html(html_content)
            if courses:
                # Write the course page to a file
                file_path = os.path.join(repo_root_dir, "public", date, f"{course_code}.json")
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(courses, file, ensure_ascii=False, indent=2)

    # Update most_recent.txt file
    with open(os.path.join(repo_root_dir, "public", "most_recent.txt"), "w", encoding="utf-8") as file:
        file.write(date)

    # Update the course_codes.json file
    with open(os.path.join(repo_root_dir, "public", "course_codes.json"), "w", encoding="utf-8") as file:
        json.dump(course_codes, file, ensure_ascii=False)

    pushChanges(repo_root_dir, f"Add course schedules for {date}")

