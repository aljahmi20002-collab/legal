# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
from bs4 import BeautifulSoup

class LabourLawUpdates(Document):
	pass

# This is the function that will be called by the scheduler hook.
# All the logic is now safely inside this function.
def scrape_labour_laws():
    url = "https://labourlawreporter.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an error for bad responses
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Failed to fetch data from {url}: {e}", "Labour Law Scraper")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    # This selector is a guess and may need to be adjusted if the website's HTML changes.
    updates = soup.find_all("div", class_="law-update-card") 

    if not updates:
        frappe.log_error("No law updates found with the current HTML selector.", "Labour Law Scraper")
        return

    new_laws_found = []
    for update in updates:
        try:
            law_title = update.find("h2").text.strip()
            effective_date = update.find("span", class_="date").text.strip()
            description = update.find("p").text.strip()
            source_url = update.find("a")["href"]

            if frappe.db.exists("Labour Law Updates", {"source_url": source_url}):
                continue

            new_law = frappe.get_doc({
                "doctype": "Labour Law Updates",
                "law_title": law_title,
                "effective_date": effective_date,
                "description": description,
                "source_url": source_url,
                "status": "New"
            })
            new_law.insert(ignore_permissions=True) # Ignore permissions for background jobs
            new_laws_found.append(new_law.as_dict())

        except Exception as e:
            frappe.log_error(f"Error parsing a law update: {e}", "Labour Law Scraper")
            continue
            
    frappe.db.commit()
    
    if new_laws_found:
        notify_hr(new_laws_found)

def notify_hr(new_laws):
    if not new_laws:
        return

    message = "<h3>New Labour Law Updates</h3><ul>"
    for law in new_laws:
        doc_link = frappe.utils.get_url_to_form(law.get('doctype'), law.get('name'))
        message += f"<li><a href='{doc_link}'>{law.get('law_title')}</a> (Source: <a href='{law.get('source_url')}'>Link</a>)</li>"
    message += "</ul>"

    frappe.sendmail(
        recipients=["dir@gretisindia.com"],
        subject="New Labour Law Updates",
        message=message,
        delayed=True
    )
