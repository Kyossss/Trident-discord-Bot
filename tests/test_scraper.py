import os
from scraper import parse_resource_html

def test_parse_resource_html():
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_page.html')
    with open(fixture_path, 'r', encoding='utf-8') as f:
        html = f.read()

    details = parse_resource_html(html)
    
    assert details['title'] == 'MyPlugin'
    assert details['version'] == '1.0.0'
    assert details['thumbnail'] == 'https://builtbybit.com/data/resource_icons/12/12345.jpg'
    assert details['date'] == 'May 3, 2021'
