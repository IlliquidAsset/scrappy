import requests
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import partial_ratio

BASE_URL = "https://nashville-tn.mygovonline.com/mod.php?mod=propertytax&mode=public_lookup&action=&title="

# Function to confirm matches interactively
def confirm_match(input_name, matched_name, confirmed_matches, threshold=80):
    """
    Ask the user to confirm fuzzy matches interactively.
    """
    if input_name.lower() == matched_name.lower():
        return True
    if partial_ratio(input_name.lower(), matched_name.lower()) >= threshold:
        if matched_name not in confirmed_matches:
            while True:
                response = input(f"Does '{input_name}' match '{matched_name}'? (y/n): ").strip().lower()
                if response in ['y', 'n']:
                    confirmed_matches[matched_name] = response == 'y'
                    return confirmed_matches[matched_name]
                print("Invalid input. Please enter 'y' for yes or 'n' for no.")
        else:
            return confirmed_matches[matched_name]
    return False

# Function to scrape property data and generate PDF links
def scrape_property_data(owner_names, tax_year="2024"):
    results = []
    session = requests.Session()
    confirmed_matches = {}  # To store user-confirmed matches

    for owner_name in owner_names:
        seen_accounts = set()
        page = 1

        while True:
            payload = {
                "selectMenu": "individual",
                "tax_year": tax_year,
                "owner_name": owner_name.strip(),
                "page": page
            }

            print(f"Searching for owner: {owner_name}, Page: {page}")
            try:
                response = session.post(BASE_URL, data=payload)
                if response.status_code == 500:
                    print(f"Server error (HTTP 500) for {owner_name}, Page: {page}. Retrying...")
                    break  # Avoid retrying indefinitely

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    table = soup.find("table", id="data")

                    if not table:
                        print(f"No table found on page {page} for {owner_name}. Stopping.")
                        break

                    rows = table.find_all("tr", class_="odd")
                    if not rows:
                        print(f"No rows found on page {page} for {owner_name}. Stopping.")
                        break

                    new_results = 0
                    for row in rows:
                        cells = row.find_all("td")
                        if len(cells) >= 5:
                            account = cells[3].text.strip()
                            if account in seen_accounts:
                                continue

                            owner = cells[1].text.strip()
                            address = cells[2].text.strip()
                            year = cells[4].text.strip()
                            link_suffix = cells[5].find("a")["href"] if cells[5].find("a") else None
                            
                            # Construct the full property link
                            full_link = f"https://nashville-tn.mygovonline.com/{link_suffix}" if link_suffix else None

                            # Construct the PDF link from the property link
                            id_value = link_suffix.split("id=")[1].split("&")[0] if link_suffix and "id=" in link_suffix else None
                            pdf_link = f"https://nashville-tn.mygovonline.com/mod.php?mod=propertytax&mode=PDFBill&viewtype=public&bill[]={id_value}&show_ocr=1" if id_value else None

                            # Use fuzzy matching to confirm the name
                            if confirm_match(owner_name, owner, confirmed_matches):
                                results.append({
                                    "Input Name": owner_name,
                                    "Matched Name": owner,
                                    "Address": address,
                                    "Account": account,
                                    "Year": year,
                                    "Link": full_link,
                                    "PDF Link": pdf_link,
                                })
                                seen_accounts.add(account)
                                new_results += 1
                                print(f"Match confirmed: {owner}")
                            else:
                                print(f"Match rejected: {owner}")

                    if new_results == 0:
                        print(f"No new results on page {page} for {owner_name}. Stopping.")
                        break

                else:
                    print(f"Failed to fetch data for {owner_name}, Page: {page}: HTTP {response.status_code}")
                    break

                page += 1
            except requests.RequestException as e:
                print(f"Error fetching data for {owner_name}, Page: {page}: {e}")
                break

    return results
