import os
import re
import sys
import logging
import bibtexparser

HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;"
}

def html_escape(text):
    """Produce entities within text."""
    if not text:
        return ""
    return "".join(HTML_ESCAPE_TABLE.get(c, c) for c in text)

def clean_text(text):
    """Strip LaTeX commands and fix spacing."""
    if not text:
        return ""
    
    text = re.sub(r'\\[a-zA-Z]+\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = text.replace('{', '').replace('}', '').replace('\n', ' ')
    
    text = re.sub(r'\s+', ' ', text)
    text = text.replace(' ,', ',')
    
    return text.strip()

def format_authors(author_string, target_author="Hari"):
    """Convert 'Last, First' to 'F. Last' and bold a specific author."""
    if not author_string or author_string == "Unknown Author":
        return author_string

    # Split authors by 'and'
    authors = [a.strip() for a in author_string.split(' and ')]
    formatted_authors = []

    for author in authors:
        # Handle "Last, First" format
        if ',' in author:
            parts = author.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            # Grab the very first letter of the first name
            first_initial = first_name[0] if first_name else ""
            formatted_name = f"{first_initial}. {last_name}"
            
        # Handle "First Last" format (fallback)
        else:
            parts = author.split()
            if len(parts) > 1:
                last_name = parts[-1]
                first_initial = parts[0][0]
                formatted_name = f"{first_initial}. {last_name}"
            else:
                formatted_name = author # Fallback for single-word names

        # Automatically bold your name
        if target_author in formatted_name:
            formatted_name = f"<strong>{formatted_name}</strong>"

        formatted_authors.append(formatted_name)

    # Join with proper grammar
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return f"{formatted_authors[0]} and {formatted_authors[1]}"
    else:
        return ", ".join(formatted_authors[:-1]) + f", and {formatted_authors[-1]}"

def generate_slug(title):
    """Create a URL-friendly slug from the paper title."""
    title_clean = clean_text(title)
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title_clean.lower())
    return re.sub(r'[\s-]+', '-', slug)[:50].strip('-')

def parse_date(entry):
    """Extract date or year and ensure it matches YYYY-MM-DD for Jekyll."""
    raw_date = entry.get('date', entry.get('year', '1900-01-01'))
    raw_date = clean_text(raw_date)
    
    parts = raw_date.split('-')
    if len(parts) == 1:
        return f"{parts[0]}-01-01"
    elif len(parts) == 2:
        return f"{parts[0]}-{parts[1].zfill(2)}-01"
    else:
        return raw_date

def generate_citation(entry, title, venue):
    """Build a basic academic citation string matching the target format."""
    author_raw = entry.get('author', 'Unknown Author')
    author_clean = clean_text(author_raw)
    
    # Run the new author formatting function
    author_formatted = format_authors(author_clean)
    
    year = entry.get('year', parse_date(entry).split('-')[0])
    
    volume = clean_text(entry.get('volume', ''))
    pages = clean_text(entry.get('pages', ''))
    
    start_page = ""
    if pages:
        start_page = pages.split('-')[0].strip()
    
    # Build citation using the newly formatted author string
    citation = f"{author_formatted} ({year}). &quot;{title}.&quot;"
    
    if venue:
        citation += f" <i>{venue}</i>"
        
    if volume:
        citation += f" <strong>{volume}</strong>"
        
    if start_page:
        citation += f", {start_page}"
        
    citation += f" ({year})."
    
    return citation 

def create_md_from_bib(filename: str):
    """Read the BibTeX file and generate Jekyll markdown files."""
    
    logging.getLogger('bibtexparser.bparser').setLevel(logging.CRITICAL)
    parser = bibtexparser.bparser.BibTexParser()
    parser.ignore_nonstandard_types = False
    
    with open(filename, 'r', encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file, parser=parser)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.abspath(os.path.join(script_dir, "../_publications/"))
    os.makedirs(out_dir, exist_ok=True)

    for entry in bib_database.entries:
        
        title = clean_text(entry.get('title', 'Untitled'))
        pub_date = parse_date(entry)
        url_slug = generate_slug(title)
        html_filename = f"{pub_date}-{url_slug}"
        
        entry_type = entry.get('ENTRYTYPE', 'article').lower()
        if entry_type == 'preprint':
            category = 'preprints'
        elif entry_type == 'inproceedings':
            category = 'proceedings'
        else:
            category = 'manuscripts' 
            
        venue = clean_text(entry.get('journal', entry.get('booktitle', '')))
        note = clean_text(entry.get('note', ''))
        
        slidesurl = entry.get('slidesurl', entry.get('slides', ''))
        bibtexurl = entry.get('bibtexurl', entry.get('bibtex', ''))
        
        paper_url = entry.get('URL', '')
        if not paper_url and 'doi' in entry:
            paper_url = f"https://doi.org/{entry['doi']}"
        if not paper_url and entry.get('archivePrefix') == 'arXiv' and 'eprint' in entry:
            paper_url = f"https://arxiv.org/abs/{entry['eprint']}"

        citation = generate_citation(entry, title, venue)

        md = f"---\ntitle: \"{html_escape(title)}\"\n"
        md += "collection: publications\n"
        md += f"category: {category}\n"
        md += f"permalink: /publication/{html_filename}\n"
        
        if note:
            md += f"excerpt: '{html_escape(note)}'\n"
            
        md += f"date: {pub_date}\n"
        md += f"venue: '{html_escape(venue)}'\n"
        
        if slidesurl:
            md += f"slidesurl: '{slidesurl}'\n"
        if paper_url:
            md += f"paperurl: '{paper_url}'\n"
        if bibtexurl:
            md += f"bibtexurl: '{bibtexurl}'\n"
            
        safe_citation = citation.replace("'", "&apos;")
        md += f"citation: '{safe_citation}'\n"
        md += "---\n"
        
        filepath = os.path.join(out_dir, f"{html_filename}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)
            
        print(f"Successfully generated: {html_filename}.md")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 pubsFromBib-mine.py [filename.bib]', file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    create_md_from_bib(filename)