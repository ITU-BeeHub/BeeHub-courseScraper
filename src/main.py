from bs4 import BeautifulSoup
import requests
import os
import datetime

base_url = "https://www.sis.itu.edu.tr/TR/ogrenci/ders-programi/ders-programi.php?seviye=LS"
date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def fetchCoursePage(course_code : str) -> list[str]:
    url = f"{base_url}&derskodu={course_code}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # print the div with the class "table-responsive"
    table = soup.find("div", class_="table-responsive")
    
    #convert table to csv format
    rows = []
    for i, row in enumerate(table.find_all("tr")):
        if i >= 1:  # skip the first row (turkish headers)
            rows.append(",".join([cell.get_text() for cell in row.find_all(["td", "th"])]) + "\n")
    
    return rows

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
    os.mkdir(f"../public/{date}")

    for course_code in course_codes:

        # Fetch the course page
        rows = fetchCoursePage(course_code)

        # Write the course page to a file
        with open(f"../public/{date}/{course_code}.csv", "w", encoding="utf-8") as file:
            file.write("".join(rows))
