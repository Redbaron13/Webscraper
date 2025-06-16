# modules/parser.py
from requests_html import Element # Assuming requests_html.Element for type hinting

def get_element_path(element: Element) -> str:
    """Generates a simplified path for an element (e.g., html > body > div > p)."""
    path_parts = []
    # element.element is the lxml element
    current_lxml_element = element.element

    while current_lxml_element is not None:
        # lxml elements have a 'tag' attribute which is the tag name
        tag_name = current_lxml_element.tag

        # If the tag is not a string (e.g., it's a comment or PI node), stop.
        if not isinstance(tag_name, str):
            break

        path_parts.append(tag_name)

        # Stop if we've reached the 'html' tag (it's the topmost standard element)
        if tag_name == 'html':
            break

        parent_lxml_element = current_lxml_element.getparent()
        # If there's no parent, we're at the root of the fragment or document
        if parent_lxml_element is None:
            break
        current_lxml_element = parent_lxml_element

    path_parts.reverse()

    # If path_parts is empty (e.g., parsing a comment node directly or malformed fragment),
    # return a placeholder. Otherwise, join the parts.
    return ' > '.join(path_parts) if path_parts else 'document_fragment'


def parse_html_tags_from_list(elements: list[Element]) -> list[dict]:
    """
    Parses a list of HTML elements (e.g., from response.html.find('*'))
    and extracts tag information including type, content, location, and attributes.

    Args:
        elements: A list of Element objects from requests-html.

    Returns:
        A list of dictionaries, where each dictionary represents a tag and its info.
        Each dictionary contains:
        {
            'tag_type': str,    # E.g., 'div', 'p', 'a'
            'content': str,     # Text content of the tag, normalized whitespace
            'location': str,    # Simplified path like 'html > body > div > p'
            'attributes': dict  # Dictionary of attributes, e.g., {'id': 'main', 'class': 'container'}
        }
    """
    extracted_data = []

    for element in elements:
        # Ensure it's a requests_html.Element and has a string tag
        if not isinstance(element, Element) or \
           not hasattr(element, 'tag') or \
           not isinstance(element.tag, str):
            # Skip if not a proper element (e.g., a Comment object from lxml)
            continue

        tag_type = element.tag

        # Get direct text content of the element, normalize whitespace.
        # element.text extracts only the text directly within this element, not children.
        content = element.text if element.text else ""
        content = ' '.join(content.split()).strip() # Normalize and strip

        location = get_element_path(element)
        attributes = dict(element.attrs) # attrs is a dict-like object from requests-html

        extracted_data.append({
            'tag_type': tag_type,
            'content': content,
            'location': location,
            'attributes': attributes
        })

    return extracted_data

if __name__ == '__main__':
    # This section is for basic testing of the parser module.
    # It requires requests_html to be installed.
    from requests_html import HTML # For creating an HTML object from a string

    sample_html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <div id="main" class="container">
            <h1>Welcome</h1>
            <p>This is a <span>test</span> paragraph.</p>
            <p>Another paragraph with a <a href="/more" class="external">link</a>.</p>
            <ul class="items">
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </div>
        <div id="footer">
            <p>&copy; 2023 Test Inc.</p> <!-- Added some content -->
        </div>
    </body>
    </html>
    """

    html_doc = HTML(html=sample_html_content) # Create an HTML object
    all_elements = html_doc.find('*') # Get all elements (returns a list of Element objects)

    print(f"Found {len(all_elements)} elements to parse from sample HTML.")

    parsed_tags = parse_html_tags_from_list(all_elements)

    if parsed_tags:
        print(f"Successfully parsed {len(parsed_tags)} tags.")
        # Print info for a few specific tags for better verification
        for tag_info in parsed_tags:
            if tag_info['tag_type'] in ['html', 'h1', 'span', 'a', 'li', 'title'] and \
               (tag_info['content'] or tag_info['tag_type'] == 'html'): # Show html tag even if no direct content
                print(f"  Tag Type: {tag_info['tag_type']}")
                print(f"    Content: '{tag_info['content'][:100]}{'...' if len(tag_info['content']) > 100 else ''}'")
                print(f"    Location: {tag_info['location']}")
                print(f"    Attributes: {tag_info['attributes']}")
            elif tag_info['tag_type'] == 'p' and "2023" in tag_info['content']: # Specific check for footer p
                 print(f"  Tag Type: {tag_info['tag_type']} (Footer)")
                 print(f"    Content: '{tag_info['content']}'")
                 print(f"    Location: {tag_info['location']}")
                 print(f"    Attributes: {tag_info['attributes']}")


    else:
        print("No tags were parsed. Check the HTML content or parsing logic.")

    print("\n--- Testing get_element_path directly ---")
    h1_element = html_doc.find('h1', first=True)
    if h1_element:
        print(f"Path for h1: {get_element_path(h1_element)}") # Expected: html > body > div > h1

    span_element = html_doc.find('span', first=True)
    if span_element:
        print(f"Path for span: {get_element_path(span_element)}") # Expected: html > body > div > p > span

    html_tag_element = html_doc.find('html', first=True)
    if html_tag_element:
        print(f"Path for html tag: {get_element_path(html_tag_element)}") # Expected: html

    # Test with a comment or DOCTYPE (though find('*') might not return them as Elements)
    # If we had a comment element, its path might be 'document_fragment' or path to its parent.
    # For now, the parser focuses on actual tags returned by find('*').
    print("\n--- Parser module test complete ---")
