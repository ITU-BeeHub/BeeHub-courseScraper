import os
import requests
import datetime
import json

from github import pushChanges
from bs4 import BeautifulSoup

BASE_URL = "https://obs.itu.edu.tr/public/DersProgram"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6533.100 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE_URL}",
    "Accept": "application/json"
}

# Used for deriving fields in the new JSON format
DAY_MAP_TR_EN = {
    'Pazartesi': 'Monday',
    'Salı': 'Tuesday',
    'Çarşamba': 'Wednesday',
    'Perşembe': 'Thursday',
    'Cuma': 'Friday',
    'Cumartesi': 'Saturday',
    'Pazar': 'Sunday'
}

PROGRAM_SEVIYE_MAP = {
    'LS': 'lisans',
    'YL': 'yuksek-lisans',
    'DR': 'doktora'
}


date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
guncellenme_saati = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

repo_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_courses_html(html_content, ders_brans_kodu_id, program_seviye):
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

        def get_parts(element):
            return [s.strip() for s in element.get_text(separator='\n').strip().split('\n') if s.strip()]

        # --- Scrape data from table cells ---
        crn = get_text(cols[0])
        course_code_anchor = cols[1].find('a')
        course_code = get_text(course_code_anchor) if course_code_anchor else get_text(cols[1])
        course_title = get_text(cols[2])
        teaching_method = get_text(cols[3])
        instructor = get_text(cols[4])
        
        # Combine multi-line schedule info with spaces to match desired format
        binaKodu = ' '.join(get_parts(cols[5]))
        gunAdiTR = ' '.join(get_parts(cols[6]))
        baslangicSaati = ' '.join(get_parts(cols[7]))
        mekanAdi = ' '.join(get_parts(cols[8]))
        
        capacity_str = get_text(cols[9])
        enrolled_str = get_text(cols[10])
        reservation = get_text(cols[11])
        
        major_restriction_anchor = cols[12].find('a')
        major_restriction = get_text(major_restriction_anchor) if major_restriction_anchor else get_text(cols[12])

        prereq_anchor = cols[13].find('a')
        onSart = "Var" if prereq_anchor else ("Yok" if get_text(cols[13]) == "-" else get_text(cols[13]))

        credit_class_resc = get_text(cols[14])

        # --- Transform and derive data for the new format ---
        try:
            kontenjan = int(capacity_str)
        except (ValueError, TypeError):
            kontenjan = 0
        
        try:
            ogrenciSayisi = int(enrolled_str)
        except (ValueError, TypeError):
            ogrenciSayisi = 0

        dilKodu = "en-us" if course_code.endswith('E') else "tr-tr"
        programSeviyeTipi = PROGRAM_SEVIYE_MAP.get(program_seviye, program_seviye)
        
        gunAdiEN_parts = [DAY_MAP_TR_EN.get(day, '') for day in gunAdiTR.split()]
        gunAdiEN = ' '.join(filter(None, gunAdiEN_parts))

        # --- Assemble the new course data object ---
        course_data = {
            # Fields that cannot be scraped from HTML are set to None or a default
            'dersTanimiId': None,
            'akademikDonemKodu': None, 
            'programSeviyeTipiId': None,
            'webdeGoster': True,

            # Mapped and derived fields
            'crn': crn,
            'dersKodu': course_code,
            'dersBransKoduId': ders_brans_kodu_id,
            'dilKodu': dilKodu,
            'programSeviyeTipi': programSeviyeTipi,
            'dersAdi': course_title,
            'ogretimYontemi': teaching_method,
            'adSoyad': instructor,
            'mekanAdi': mekanAdi,
            'gunAdiTR': gunAdiTR,
            'gunAdiEN': gunAdiEN,
            'baslangicSaati': baslangicSaati,
            'bitisSaati': "", # Always empty in the desired format
            'binaKodu': binaKodu,
            'kontenjan': kontenjan,
            'ogrenciSayisi': ogrenciSayisi,
            'rezervasyon': reservation,
            'sinifProgram': major_restriction,
            'onSart': onSart,
            'sinifOnsart': credit_class_resc
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
    new_dir_path = os.path.join(repo_root_dir, "public", date)
    os.makedirs(new_dir_path, exist_ok=True)

    # Step 2: For each course code, get courses and save to file
    for code in course_codes:
        ders_brans_kodu_id = code['bransKoduId']
        course_code_prefix = code['dersBransKodu'] # e.g. "AKM"
        html_content = get_courses(program_seviye, ders_brans_kodu_id)
        
        if html_content:
            parsed_courses = parse_courses_html(html_content, ders_brans_kodu_id, program_seviye)
            if parsed_courses:
                # Create the final dictionary structure for this file
                final_data = {
                    "dersProgramList": parsed_courses,
                    "guncellenmeSaati": guncellenme_saati
                }
                
                # Write the course page to a file
                file_path = os.path.join(new_dir_path, f"{course_code_prefix}.json")
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(final_data, file, ensure_ascii=False, indent=2)

    # Update most_recent.txt file
    with open(os.path.join(repo_root_dir, "public", "most_recent.txt"), "w", encoding="utf-8") as file:
        file.write(date)

    # Update the course_codes.json file
    with open(os.path.join(repo_root_dir, "public", "course_codes.json"), "w", encoding="utf-8") as file:
        json.dump(course_codes, file, ensure_ascii=False)

    pushChanges(repo_root_dir, f"Add course schedules for {date}")

