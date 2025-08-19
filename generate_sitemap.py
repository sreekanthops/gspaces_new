# generate_sitemap.py

from main import app              # import your Flask app
import xml.etree.ElementTree as ET
from datetime import datetime, UTC # Import UTC from datetime module

def build_sitemap():
    # Collect every GET route that has no URL parameters
    urls = []
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            # exclude non-GET, HEAD, OPTIONS and routes with <variables>
            if "GET" in rule.methods and not rule.arguments:
                urls.append(rule.rule)

    # Build XML structure
    urlset = ET.Element("urlset", {
        "xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"
    })
    
    # FIX: Use datetime.now(datetime.UTC) for timezone-aware UTC datetime
    today = datetime.now(UTC).date().isoformat() 

    for path in sorted(set(urls)):
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"https://gspaces.in{path}"
        ET.SubElement(url, "lastmod").text = today
        ET.SubElement(url, "changefreq").text = "monthly"
        ET.SubElement(url, "priority").text = "0.6"

    # Write to file
    tree = ET.ElementTree(urlset)
    tree.write("sitemap.xml", encoding="utf-8", xml_declaration=True)
    print(f"Wrote sitemap.xml with {len(urls)} URLs:")
    for u in sorted(set(urls)):
        print("  •", u)

if __name__ == "__main__":
    build_sitemap()
