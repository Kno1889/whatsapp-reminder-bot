#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
import re
import requests
from PIL import Image, ImageDraw, ImageFont
import io

def get_page_verse_ranges(api_base_url, pages_to_fetch=10):
    """
    Call the alquran.cloud API to get the starting and ending verses for each page.
    
    Args:
        api_base_url: The base URL for the Quran API
        pages_to_fetch: Number of pages to fetch (default: 10)
        
    Returns:
        A dictionary mapping page numbers to verse ranges (start_chapter, start_verse, end_chapter, end_verse)
    """
    print(f"Fetching page verse ranges from API...")
    
    try:
        page_verses = {}
        retries = 2  # Number of retries for failed requests
        
        # Fetch data for each page
        for page_num in range(1, pages_to_fetch + 1):
            success = False
            retry_count = 0
            
            while not success and retry_count <= retries:
                try:
                    # Make API request to get page data with timeout
                    url = f"{api_base_url}/page/{page_num}/quran-uthmani"
                    print(f"Requesting {url}...")
                    
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code != 200:
                        print(f"API error on page {page_num}: {response.status_code}")
                        retry_count += 1
                        if retry_count <= retries:
                            print(f"Retrying... (attempt {retry_count}/{retries})")
                            continue
                        else:
                            break
                        
                    # Parse the response
                    data = response.json()
                    
                    if 'data' not in data:
                        print(f"Invalid response structure for page {page_num}: 'data' field missing")
                        retry_count += 1
                        if retry_count <= retries:
                            print(f"Retrying... (attempt {retry_count}/{retries})")
                            continue
                        else:
                            break
                    
                    if 'ayahs' not in data['data'] or not data['data']['ayahs']:
                        print(f"Invalid or empty response structure for page {page_num}: 'ayahs' field missing or empty")
                        retry_count += 1
                        if retry_count <= retries:
                            print(f"Retrying... (attempt {retry_count}/{retries})")
                            continue
                        else:
                            break
                    
                    ayahs = data['data']['ayahs']
                    
                    # Get first and last ayah (verse) on the page
                    first_ayah = ayahs[0]
                    last_ayah = ayahs[-1]
                    
                    # Store the verse range for this page
                    page_verses[page_num] = {
                        'start_chapter': first_ayah['surah']['number'],
                        'start_verse': first_ayah['numberInSurah'],
                        'end_chapter': last_ayah['surah']['number'],
                        'end_verse': last_ayah['numberInSurah'],
                        'all_verses': [a['numberInSurah'] for a in ayahs] # Store all verse numbers on this page
                    }
                    
                    print(f"API Page {page_num}: Surah {first_ayah['surah']['number']}:{first_ayah['numberInSurah']} to "
                          f"Surah {last_ayah['surah']['number']}:{last_ayah['numberInSurah']} "
                          f"(Total verses: {len(ayahs)})")
                    
                    success = True
                
                except requests.exceptions.Timeout:
                    print(f"API request timeout for page {page_num}")
                    retry_count += 1
                    if retry_count <= retries:
                        print(f"Retrying... (attempt {retry_count}/{retries})")
                    else:
                        print(f"Max retries reached for page {page_num}, skipping")
                except requests.exceptions.RequestException as e:
                    print(f"API request error for page {page_num}: {e}")
                    retry_count += 1
                    if retry_count <= retries:
                        print(f"Retrying... (attempt {retry_count}/{retries})")
                    else:
                        print(f"Max retries reached for page {page_num}, skipping")
                except (KeyError, ValueError, TypeError) as e:
                    print(f"Error parsing API response for page {page_num}: {e}")
                    retry_count += 1
                    if retry_count <= retries:
                        print(f"Retrying... (attempt {retry_count}/{retries})")
                    else:
                        print(f"Max retries reached for page {page_num}, skipping")
        
        print(f"Successfully fetched verse ranges for {len(page_verses)} pages")
        
        if not page_verses:
            print("Warning: No page verse ranges were fetched from the API")
            print("You might want to try again later or check your internet connection")
            return None
            
        return page_verses
        
    except Exception as e:
        print(f"Error fetching page data from API: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_chapter_start_page(pdf_path, chapter_num, start_page=28, found_pages=None):
    """
    Find the page where a specific chapter starts.
    
    Args:
        pdf_path: Path to the PDF file
        chapter_num: Chapter number to find
        start_page: Page to start searching from (default: 28)
        found_pages: List of already found pages to avoid duplicates
        
    Returns:
        The page number where the chapter starts, or None if not found
    """
    try:
        # Initialize found_pages if not provided
        if found_pages is None:
            found_pages = []
            
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        print(f"Searching for Chapter {chapter_num} starting from page {start_page}")
        print(f"Avoiding already found pages: {found_pages}")
        
        # Very specific patterns to match exact surah title formatting
        # For strict title match including word boundaries and trailing context
        # This reduces the chance of matching partial titles or references
        exact_title_patterns = [
            f"\\b{chapter_num}\\. The\\b",
            f"\\b{chapter_num}\\. Al-\\w+\\b",
            f"\\b{chapter_num}\\. [A-Z][a-z]+\\b"
        ]
        
        # Specific title check for this chapter - different chapters have different naming patterns
        specific_chapter_patterns = {
            1: ["1. The Opening", "1. Al-Fatiha"],
            2: ["2. The Cow", "2. Al-Baqarah"],
            3: ["3. The Family of", "3. Aali Imran", "3. Âli-'Imrân"],
            4: ["4. Women", "4. An-Nisa"],
            7: ["7. The Heights", "7. Al-A'raf"],
            9: ["9. Repentance", "9. At-Tawbah"]
        }
        
        # Get specific patterns for this chapter if available
        chapter_specific_patterns = specific_chapter_patterns.get(chapter_num, [])
        
        # Search through pages
        for page_num in range(start_page, min(start_page + 200, total_pages)):
            # Skip pages that we've already identified as containing other surahs
            if page_num in found_pages:
                print(f"Skipping page {page_num} as it's already assigned to another surah")
                continue
                
            page = doc[page_num]
            text = page.get_text()
            
            # Get blocks for detailed analysis
            blocks = page.get_text("dict")["blocks"]
            
            # Track if we have a strong match
            strong_match = False
            match_text = ""
            
            # Check for specific chapter patterns first - most reliable
            for pattern in chapter_specific_patterns:
                if pattern in text:
                    strong_match = True
                    match_text = pattern
                    break
            
            # If no specific pattern matched, try the generic patterns
            if not strong_match:
                for pattern in exact_title_patterns:
                    match = re.search(pattern, text)
                    if match:
                        match_text = match.group(0)
                        # Verify this is a title, not just a reference
                        # Check surrounding context to ensure it's not a reference
                        pre_context = text[max(0, match.start()-30):match.start()].lower()
                        if any(ref in pre_context for ref in ["see", "chapter", "surah", "mentioned in", "refer to"]):
                            continue
                        
                        # This looks like a real title
                        strong_match = True
                        break
            
            # If we don't have a strong match, skip this page
            if not strong_match:
                continue
                
            # Additional verification: Look for distinctive formatting markers of a surah page
            
            # 1. Check for Arabic name in parentheses - common in surah headers
            arabic_name_pattern = r"\(\s*[A-Za-z\-']+\s*\)"
            has_arabic_name = bool(re.search(arabic_name_pattern, text))
            
            # 2. Check for bismillah - appears at start of most surahs
            has_bismillah = "In the Name of Allah" in text
            
            # 3. Check for intro text - usually red/italic text describing the surah
            surah_intro_patterns = [
                r"This .+s[ûu]rah",
                "Medinian sûrah",
                "Meccan sûrah",
                "This sûrah",
                "verses were revealed"
            ]
            has_intro = any(re.search(pattern, text) for pattern in surah_intro_patterns)
            
            # 4. Look for centered title formatting
            is_centered_title = False
            for block in blocks:
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    line_text = "".join([span["text"] for span in line["spans"]])
                    
                    # Check if this line contains our chapter title
                    if match_text in line_text:
                        # Check position - titles are usually centered
                        line_x_center = (line["bbox"][0] + line["bbox"][2]) / 2
                        page_width = page.rect.width
                        
                        # Check font size - titles are usually larger
                        font_size = max([span["size"] for span in line["spans"]], default=0)
                        
                        # If line is centered and has large font, it's likely a title
                        if (abs(line_x_center - page_width/2) < page_width/4 and font_size > 14):
                            is_centered_title = True
                            break
            
            # Count how many surah indicators we have 
            indicator_count = sum([
                is_centered_title,
                has_arabic_name, 
                has_bismillah,
                has_intro
            ])
            
            # Very strict check: require at least 3 indicators for a strong match
            if indicator_count >= 3:
                print(f"Found chapter {chapter_num} on page {page_num} with strong surah formatting")
                print(f"  Title: {match_text}")
                print(f"  Has Arabic name: {has_arabic_name}")
                print(f"  Has bismillah: {has_bismillah}")
                print(f"  Has introduction: {has_intro}")
                print(f"  Is centered title: {is_centered_title}")
                print(f"  Total indicators: {indicator_count}")
                doc.close()
                return page_num
            
            # Less strict but still reasonable: 2 indicators including the centered title
            if indicator_count >= 2 and is_centered_title:
                print(f"Found chapter {chapter_num} on page {page_num} with partial surah formatting")
                print(f"  Title: {match_text}")
                print(f"  Indicator count: {indicator_count}")
                doc.close()
                return page_num
                
        # If we get here, we couldn't find the chapter
        print(f"Could not find start page for Chapter {chapter_num}")
        doc.close()
        return None
        
    except Exception as e:
        print(f"Error finding chapter start page: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_verses_with_counter(pdf_path, chapter, verse_start, verse_end=None, output_dir=None, chapter_start_page=None):
    """
    Extract pages containing specified verses with improved multi-page handling.
    
    Args:
        pdf_path: Path to the PDF file
        chapter: Chapter number
        verse_start: Starting verse number
        verse_end: Ending verse number (default: same as verse_start)
        output_dir: Directory to save output images
        chapter_start_page: Page where the chapter starts (optional)
        
    Returns:
        True if successful, False otherwise
    """
    if verse_end is None:
        verse_end = verse_start
        
    print(f"Extracting Surah {chapter}, verses {verse_start}-{verse_end}...")
    
    try:
        # Set up output directory
        if output_dir is None:
            output_dir = os.path.expanduser("~/Desktop/quran_images")
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Use provided chapter start page or find it
        if chapter_start_page is None:
            chapter_start_page = find_chapter_start_page(pdf_path, chapter)
            if not chapter_start_page:
                print(f"Could not find start page for Chapter {chapter}")
                return False
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print("PDF opened successfully")
        
        # Find the next chapter's start page to set boundary
        next_chapter = chapter + 1
        next_chapter_start = find_chapter_start_page(pdf_path, next_chapter, chapter_start_page + 1)
        
        # Set search limit - either next chapter or a reasonable number of pages
        if next_chapter_start:
            search_limit = next_chapter_start
            print(f"Found next chapter (Surah {next_chapter}) starting at page {next_chapter_start}")
        else:
            # If we can't find the next chapter, limit based on current chapter
            search_limit = min(chapter_start_page + 50, total_pages)
            print(f"Could not find next chapter, will search up to page {search_limit}")
        
        print(f"Searching for verses {verse_start}-{verse_end} between pages {chapter_start_page} and {search_limit-1}")
        
        # Flag to indicate whether we need to look for a surah description
        # This happens when verse 1 is included in the range
        include_surah_description = (verse_start == 1)
        if include_surah_description:
            print("Verse 1 requested - will look for surah description")
        
        # Dictionary to store verse numbers and their positions on each page
        page_verses = {}
        
        # Track which verses we're looking for and which we've found
        target_verses = set(range(verse_start, verse_end + 1))
        found_verses = set()
        
        # Store surah description if found
        surah_description = None
        surah_description_position = None
        
        # Track which pages contain our target verses
        relevant_pages = []
        
        # First pass: identify all verses and their positions with high confidence
        for page_num in range(chapter_start_page, search_limit):
            page = doc[page_num]
            
            # Get text with detailed structure
            blocks = page.get_text("dict")["blocks"]
            
            # Track verses found on this page
            verses_on_page = {}  # {verse_num: [(y_position, confidence, bbox)]}
            
            # Check for surah description on the chapter start page
            if include_surah_description and page_num == chapter_start_page:
                # Look for the description text that typically appears in red before verse 1
                description_blocks = []
                description_y_min = float('inf')
                description_y_max = 0
                
                for block in blocks:
                    if "lines" not in block:
                        continue
                    
                    # Skip very top/bottom portions
                    block_y_min = block["bbox"][1]
                    block_y_max = block["bbox"][3]
                    page_height = page.rect.height
                    
                    if block_y_min < page_height * 0.05 or block_y_max > page_height * 0.9:
                        continue
                    
                    # Check if any spans in this block have red text (likely description)
                    has_red_text = False
                    is_italic = False
                    block_text = ""
                    
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_text = span["text"].strip()
                            if not span_text:
                                continue
                                
                            block_text += span["text"] + " "
                            
                            # Check for red text (common in descriptions)
                            # Red text typically has a higher value in the "color" field
                            if span["color"] > 0 and not span_text.isdigit():
                                has_red_text = True
                            
                            # Check for italic text (common in descriptions)
                            # Italic is typically indicated by the flags field
                            if span["flags"] & 4:  # 4 is the flag for italic
                                is_italic = True
                    
                    # If this block has red or italic text, it might be part of the description
                    # Also check that it's not just a number or very short text, as that's likely not part of description
                    if (has_red_text or is_italic) and len(block_text.strip()) > 10:
                        description_blocks.append(block)
                        description_y_min = min(description_y_min, block_y_min)
                        description_y_max = max(description_y_max, block_y_max)
                        print(f"Found potential surah description: {block_text.strip()}")
                
                if description_blocks:
                    # We found some text that might be the surah description
                    surah_description = description_blocks
                    surah_description_position = (description_y_min, description_y_max)
                    print(f"Identified surah description at y-position: {description_y_min} to {description_y_max}")
            
            # Process each text block for verses
            for block in blocks:
                if "lines" not in block:
                    continue
                
                # Skip headers/footers (typically at very top or bottom)
                block_y_min = block["bbox"][1]
                block_y_max = block["bbox"][3]
                page_height = page.rect.height
                
                if block_y_min < page_height * 0.1 or block_y_max > page_height * 0.9:
                    continue
                
                # Process each line
                for line in block["lines"]:
                    line_text = "".join([span["text"] for span in line["spans"]])
                    
                    # Multiple regex patterns to catch verse numbers in different formats
                    # Pattern 1: Standard format - number followed by period and space
                    verse_matches = list(re.finditer(r'(\d+)\.\s', line_text))
                    # Pattern 2: Look for verse numbers anywhere in the line
                    if not verse_matches and line_text.strip():
                        # Look for numbers followed by a period that are likely verse numbers
                        verse_matches = list(re.finditer(r'(\d+)\.\s', line_text))
                        
                        # Additional pattern to catch verse numbers with different formatting
                        if not verse_matches:
                            verse_matches = list(re.finditer(r'(?<!\d)(\d+)\.(?!\d)', line_text))
                    
                    # Only show matches that are within our target range
                    target_matches = []
                    for match in verse_matches:
                        try:
                            verse_num = int(match.group(1))
                            if verse_start <= verse_num <= verse_end:
                                target_matches.append(verse_num)
                        except ValueError:
                            continue
                    
                    if target_matches:
                        print(f"Page {page_num}: Found target verses: {target_matches}")
                    
                    for match in verse_matches:
                        try:
                            verse_num = int(match.group(1))
                            
                            # Skip unreasonable verse numbers
                            if verse_num < 1 or verse_num > 300:
                                continue
                                
                            # Look at the context after the verse number
                            match_end = match.end()
                            after_text = line_text[match_end:match_end+30] if match_end < len(line_text) else ""
                            
                            # Real verses usually have text following the number
                            if not after_text.strip():
                                continue
                            
                            # Calculate confidence based on multiple factors
                            confidence = 0
                            
                            # Look at the spans to check formatting
                            match_pos = match.start()
                            span_containing_verse = None
                            
                            # Find which span contains this verse number
                            pos = 0
                            for span in line["spans"]:
                                span_text = span["text"]
                                span_len = len(span_text)
                                
                                if pos <= match_pos < pos + span_len:
                                    span_containing_verse = span
                                    break
                                pos += span_len
                            
                            if span_containing_verse:
                                # Bold numbers are more likely to be verse numbers
                                if span_containing_verse["flags"] & 16:  # Bold
                                    confidence += 3
                                
                                # Larger font size indicates verse numbers
                                font_size = span_containing_verse["size"]
                                if font_size > 10:
                                    confidence += 1
                                
                                # Check for distinctive verse format - number at beginning of line
                                if match_pos < 5:
                                    confidence += 2
                                
                                # Check length - verse numbers are usually 1-3 digits
                                verse_str = match.group(1)
                                if 1 <= len(verse_str) <= 3:
                                    confidence += 1
                                
                                # Record the y-position and bounding box for cropping
                                y_pos = line["bbox"][1]
                                bbox = line["bbox"]  # [x0, y0, x1, y1]
                                
                                # Only add verses with reasonable confidence
                                if confidence >= 2:
                                    if verse_num not in verses_on_page:
                                        verses_on_page[verse_num] = []
                                    verses_on_page[verse_num].append((y_pos, confidence, bbox))
                                    
                                    # Log target verses with highest confidence
                                    if verse_start <= verse_num <= verse_end:
                                        found_verses.add(verse_num)
                                        print(f"Page {page_num}: Found verse {verse_num} at y={y_pos} with confidence {confidence}")
                        except ValueError:
                            continue
            
            # Store all verses found on this page
            if verses_on_page:
                page_verses[page_num] = verses_on_page
                
                # Check if the page has any target verses
                has_target_verses = False
                for v in range(verse_start, verse_end + 1):
                    if v in verses_on_page:
                        has_target_verses = True
                        break
                
                if has_target_verses:
                    print(f"Page {page_num} contains target verses: {[v for v in verses_on_page.keys() if verse_start <= v <= verse_end]}")
                    relevant_pages.append(page_num)
            
            # If we've found all verses, check one more page then stop
            if found_verses == target_verses and page_num > min(relevant_pages):
                print(f"Found all target verses {verse_start}-{verse_end}, stopping search")
                break
        
        # Sort pages and ensure there are no duplicates
        relevant_pages = sorted(set(relevant_pages))
        
        # If we couldn't find any relevant pages, use the chapter start
        if not relevant_pages:
            print(f"Warning: Could not find verses {verse_start}-{verse_end}, using chapter start page")
            relevant_pages.append(chapter_start_page)
        
        # Report on which verses were found and which weren't
        if found_verses != target_verses:
            missing_verses = target_verses - found_verses
            print(f"Warning: Could not find all target verses. Missing: {sorted(list(missing_verses))}")
        
        # Process each relevant page
        output_paths = []  # Track the image files we generate
        cropped_images = []  # Store cropped images for merging
        
        for page_num in relevant_pages:
            page = doc[page_num]
            
            # Create a high-quality image of the page
            zoom = 3.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Base filename
            filename = f"quran_surah{chapter}_verse{verse_start}"
            if verse_end != verse_start:
                filename += f"-{verse_end}"
            
            # Add page number to make the filename unique, especially for multi-page extracts
            filename += f"_page{page_num}"
            
            # Create a non-cropped version first as backup
            backup_filename = filename + ".png"
            backup_path = os.path.join(output_dir, backup_filename)
            pix.save(backup_path)
            output_paths.append(backup_path)
            print(f"Saved full page as backup: {backup_path}")
            
            # Determine crop points
            should_crop = False
            crop_y_start = 0
            crop_y_end = pix.height
            
            if page_num in page_verses:
                # Find the target verses on this page
                page_target_verses = [v for v in range(verse_start, verse_end + 1) if v in page_verses[page_num]]
                
                if page_target_verses:
                    # Find the earliest target verse on this page
                    first_verse_num = min(page_target_verses)
                    positions = page_verses[page_num][first_verse_num]
                    positions.sort(key=lambda x: x[1], reverse=True)  # Sort by confidence
                    first_verse_pos = positions[0][0]  # Get y-position of highest confidence match
                    
                    # Find the latest target verse on this page
                    last_verse_num = max(page_target_verses)
                    positions = page_verses[page_num][last_verse_num]
                    positions.sort(key=lambda x: x[1], reverse=True)
                    last_verse_pos = positions[0][0]
                    
                    # Find the next verse after our target range on this page
                    next_verse_pos = None
                    next_verse_num = None
                    
                    # Look for verses that come after our last target verse on this page
                    for v in sorted(page_verses[page_num].keys()):
                        if v > last_verse_num:
                            positions = page_verses[page_num][v]
                            positions.sort(key=lambda x: x[0])  # Sort by y-position
                            next_verse_pos = positions[0][0]
                            next_verse_num = v
                            break
                    
                    # Determine crop boundaries
                    if first_verse_pos is not None:
                        # If we're including verse 1 and we found a surah description, start crop above the description
                        if include_surah_description and first_verse_num == 1 and surah_description_position and page_num == chapter_start_page:
                            # Start at the surah description
                            padding_above_description = 60
                            crop_y_start = max(0, (surah_description_position[0] * zoom) - (padding_above_description * zoom))
                            print(f"Including surah description in crop, starting at y={crop_y_start}")
                        else:
                            # Start crop above the first verse - add adequate padding
                            padding_start = 60  # pixels in original scale
                            crop_y_start = max(0, (first_verse_pos * zoom) - (padding_start * zoom))
                        
                        should_crop = True
                        print(f"Starting crop at y={crop_y_start} (above verse {first_verse_num})")
                    
                    if next_verse_pos is not None:
                        # End crop just before the next verse
                        padding_end = 20  # pixels in original scale
                        crop_y_end = min(pix.height, (next_verse_pos * zoom) - (padding_end * zoom))
                        should_crop = True
                        print(f"Ending crop at y={crop_y_end} (before verse {next_verse_num})")
                    elif last_verse_pos is not None:
                        # If no next verse, extend crop below the last verse
                        padding_after = 120  # pixels in original scale
                        crop_y_end = min(pix.height, (last_verse_pos * zoom) + (padding_after * zoom))
                        should_crop = True
                        print(f"Ending crop at y={crop_y_end} (after verse {last_verse_num})")
            
            # Apply cropping if needed
            if should_crop:
                try:
                    # Convert pixmap to PIL Image for cropping
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Ensure crop dimensions are integers
                    crop_y_start = int(crop_y_start)
                    crop_y_end = int(crop_y_end)
                    
                    # Only crop if we have meaningful boundaries
                    if crop_y_start < crop_y_end and (crop_y_start > 0 or crop_y_end < pix.height):
                        print(f"Cropping page {page_num} from y={crop_y_start} to y={crop_y_end}")
                        
                        # Crop the image
                        cropped_img = img.crop((0, crop_y_start, pix.width, crop_y_end))
                        
                        # Store the cropped image for merging
                        cropped_images.append((page_num, cropped_img))
                        
                        # Save individual cropped image
                        cropped_filename = filename + "_cropped.png"
                        output_path = os.path.join(output_dir, cropped_filename)
                        cropped_img.save(output_path)
                        output_paths.append(output_path)
                        print(f"Saved cropped image to: {output_path}")
                    else:
                        print(f"Skipping crop: invalid dimensions ({crop_y_start} to {crop_y_end})")
                except Exception as e:
                    print(f"Error during cropping: {e}")
        
        # Merge cropped images if we have multiple pages
        if len(cropped_images) > 1:
            try:
                print(f"Merging {len(cropped_images)} cropped images into a single image...")
                
                # Sort images by page number
                cropped_images.sort(key=lambda x: x[0])
                
                # Simple version: vertical stack with fixed gap
                gap = 60  # Gap between images in pixels
                
                # Calculate total height and maximum width
                total_height = sum(img.height for _, img in cropped_images) + gap * (len(cropped_images) - 1)
                max_width = max(img.width for _, img in cropped_images)
                
                # Create a new image with the calculated dimensions
                merged_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))
                
                # Paste each image with a gap
                y_position = 0
                for i, (page_num, img) in enumerate(cropped_images):
                    # Center the image horizontally
                    x_position = (max_width - img.width) // 2
                    
                    # Paste the image
                    merged_img.paste(img, (x_position, y_position))
                    
                    # Move to the next position
                    y_position += img.height
                    
                    # Add a gap after each image except the last one
                    if i < len(cropped_images) - 1:
                        # Draw a simple separator line
                        for y in range(gap):
                            for x in range(max_width):
                                # Create a subtle gradient for the gap
                                if y == gap // 2:
                                    # Draw a thin gray line in the middle
                                    merged_img.putpixel((x, y_position + y), (200, 200, 200))
                        
                        # Move past the gap
                        y_position += gap
                
                # Save the merged image
                merged_filename = f"quran_surah{chapter}_verse{verse_start}"
                if verse_end != verse_start:
                    merged_filename += f"-{verse_end}"
                merged_filename += "_merged.png"
                merged_path = os.path.join(output_dir, merged_filename)
                merged_img.save(merged_path)
                output_paths.append(merged_path)
                print(f"Saved merged image to: {merged_path}")
            except Exception as e:
                print(f"Error merging images: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"Extraction for Surah {chapter}, verses {verse_start}-{verse_end} completed")
        print(f"Created {len(output_paths)} output files")
        doc.close()
        return len(output_paths) > 0
        
    except Exception as e:
        print(f"Error extracting verses: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n============ QURAN EXTRACTION TOOL - VERSION 4.4 ============\n")
    
    try:
        # Get the path to the PDF - allow custom path as command line argument
        if len(sys.argv) > 1:
            pdf_path = sys.argv[1]
            print(f"Using PDF path from command line: {pdf_path}")
        else:
            # Default path in Downloads folder
            downloads_folder = os.path.expanduser("~/Downloads")
            pdf_path = os.path.join(downloads_folder, "THE_CLEAR_QURAN_English_Translation_by_D.pdf")
            print(f"Using default PDF path: {pdf_path}")
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            print(f"ERROR: PDF file not found: {pdf_path}")
            print(f"Please download the PDF or provide the correct path as an argument:")
            print(f"python quran_extract.py /path/to/your/quran.pdf")
            sys.exit(1)
        
        # Verify it's a valid PDF
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            print(f"PDF loaded successfully: {total_pages} pages")
        except Exception as e:
            print(f"ERROR: Could not open file as PDF: {e}")
            sys.exit(1)
        
        # Output directory
        output_dir = os.path.expanduser("~/Desktop/quran_images")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}")
            except Exception as e:
                print(f"ERROR: Failed to create output directory: {e}")
                sys.exit(1)
        else:
            # Clean up previous output files to avoid confusion
            print(f"Cleaning up existing output directory: {output_dir}")
            try:
                for file in os.listdir(output_dir):
                    if file.startswith("quran_") and file.endswith(".png"):
                        os.remove(os.path.join(output_dir, file))
                        print(f"Deleted: {file}")
            except Exception as e:
                print(f"Warning: Error while cleaning output directory: {e}")
        
        print("\n============ USING STRICT SURAH DETECTION ============\n")
        print("Using much stricter surah title detection to avoid false positives")
        print("Properly tracking found pages to avoid detecting multiple surahs on same page")
        print("Starting extraction from page 28 (after introduction pages)")
        
        # Define known surah page numbers for common surahs
        # These are manually verified and will be used as a fallback
        known_surah_pages = {
            1: 28,   # Al-Fatiha
            2: 29,   # Al-Baqarah
            3: 62,   # Aali Imran
            4: 95,   # An-Nisa
            7: 177,  # Al-A'raf
            9: 217   # At-Tawbah
        }
        
        # First test surah detection to verify it's working correctly
        print("\n============ TESTING SURAH DETECTION WITH STRICT CHECKS ============\n")
        surah_pages = {}
        found_pages = []  # Track pages we've already identified as containing surahs
        
        # Test identification of important surahs, but now skip pages we've already found
        for chapter in [1, 2, 3, 7, 9]:
            print(f"Looking for Surah {chapter}...")
            
            # Use the known page as a fallback if detection fails
            if chapter in known_surah_pages:
                print(f"Known page for Surah {chapter} is {known_surah_pages[chapter]}")
            
            # Try to detect the page, avoiding any pages we've already found
            page = find_chapter_start_page(pdf_path, chapter, start_page=28, found_pages=found_pages)
            
            # Verify the detected page isn't already assigned to another surah
            if page in found_pages:
                print(f"Warning: Page {page} was already assigned to another surah!")
                
                # Use the known page number as fallback
                if chapter in known_surah_pages:
                    page = known_surah_pages[chapter]
                    print(f"Using known page {page} for Surah {chapter} instead")
                else:
                    # If we don't have a known page, try the next page (basic fallback)
                    next_page = page + 1
                    print(f"Trying next page: {next_page}")
                    page = next_page
            
            if page:
                print(f"Successfully found Surah {chapter} on page {page}")
                surah_pages[chapter] = page
                found_pages.append(page)  # Add to the list of found pages to avoid this page for future surahs
            else:
                # If detection failed, use the known page if available
                if chapter in known_surah_pages:
                    page = known_surah_pages[chapter]
                    print(f"Detection failed, using known page {page} for Surah {chapter}")
                    surah_pages[chapter] = page
                    found_pages.append(page)
                else:
                    print(f"Failed to find Surah {chapter} and no known page available")
        
        # Verify that different surahs are on different pages
        if len(set(surah_pages.values())) < len(surah_pages):
            print("\nWARNING: Some surahs were detected on the same page. Using known page numbers instead.")
            
            # Override with known good values
            for chapter, known_page in known_surah_pages.items():
                if chapter in surah_pages:
                    surah_pages[chapter] = known_page
                    print(f"Using known page {known_page} for Surah {chapter}")
        else:
            print("\nSurah detection looks good - all surahs found on different pages.")
        
        print(f"\nSurah pages to be used: {surah_pages}")
        
        # API configuration - using the alquran.cloud API
        api_url = "http://api.alquran.cloud/v1"
        
        # Fetch page verse ranges from API
        print("\n============ FETCHING VERSE RANGES FROM API ============\n")
        page_verse_ranges = get_page_verse_ranges(api_url, pages_to_fetch=5)  # Reduced to 5 for testing
        
        if not page_verse_ranges:
            print("Failed to fetch verse ranges from API, exiting")
            sys.exit(1)
            
        # Print the verse ranges we're going to extract
        print("\nVerse ranges to extract:")
        for api_page, verse_range in page_verse_ranges.items():
            start_chapter = verse_range['start_chapter']
            start_verse = verse_range['start_verse']
            end_chapter = verse_range['end_chapter']
            end_verse = verse_range['end_verse']
            print(f"API Page {api_page}: Surah {start_chapter}:{start_verse} to {end_chapter}:{end_verse}")
        
        print("\n============ EXTRACTING VERSES FROM PDF ============\n")
        
        success_count = 0
        failure_count = 0
        
        # Process each API page
        for api_page, verse_range in page_verse_ranges.items():
            start_chapter = verse_range['start_chapter']
            start_verse = verse_range['start_verse']
            end_chapter = verse_range['end_chapter']
            end_verse = verse_range['end_verse']
            
            print(f"\n============ Processing API page {api_page} ============")
            print(f"Extracting Surah {start_chapter}:{start_verse} to {end_chapter}:{end_verse}")
            
            # Handle verses within the same chapter
            if start_chapter == end_chapter:
                print(f"Single chapter extraction: Surah {start_chapter}, verses {start_verse}-{end_verse}")
                
                # Use the known surah page if available
                chapter_page = None
                if start_chapter in surah_pages:
                    chapter_page = surah_pages[start_chapter]
                    print(f"Using page {chapter_page} for Surah {start_chapter}")
                elif start_chapter in known_surah_pages:
                    chapter_page = known_surah_pages[start_chapter]
                    print(f"Using known page {chapter_page} for Surah {start_chapter}")
                
                if not chapter_page:
                    print(f"No page found for Surah {start_chapter}, trying to search for it...")
                    chapter_page = find_chapter_start_page(pdf_path, start_chapter, found_pages=found_pages)
                    if chapter_page:
                        print(f"Found Surah {start_chapter} on page {chapter_page}")
                    
                if not chapter_page:
                    print(f"Failed to find Surah {start_chapter}, skipping extraction")
                    failure_count += 1
                    continue
                    
                success = extract_verses_with_counter(
                    pdf_path,
                    start_chapter,
                    start_verse,
                    end_verse,
                    output_dir,
                    chapter_start_page=chapter_page
                )
                
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            else:
                # Handle cross-chapter ranges separately
                print(f"Cross-chapter range detected: Surah {start_chapter} to {end_chapter}")
                
                # Get start chapter page
                start_chapter_page = None
                if start_chapter in surah_pages:
                    start_chapter_page = surah_pages[start_chapter]
                elif start_chapter in known_surah_pages:
                    start_chapter_page = known_surah_pages[start_chapter]
                else:
                    print(f"No page found for Surah {start_chapter}, trying to detect it...")
                    start_chapter_page = find_chapter_start_page(pdf_path, start_chapter, found_pages=found_pages)
                    
                # Get end chapter page
                end_chapter_page = None
                if end_chapter in surah_pages:
                    end_chapter_page = surah_pages[end_chapter]
                elif end_chapter in known_surah_pages:
                    end_chapter_page = known_surah_pages[end_chapter]
                else:
                    print(f"No page found for Surah {end_chapter}, trying to detect it...")
                    end_chapter_page = find_chapter_start_page(pdf_path, end_chapter, found_pages=found_pages)
                
                # Skip if we couldn't find either chapter
                if not start_chapter_page:
                    print(f"Failed to find Surah {start_chapter}, skipping first part of extraction")
                    failure_count += 1
                    continue
                    
                if not end_chapter_page:
                    print(f"Failed to find Surah {end_chapter}, skipping second part of extraction")
                    failure_count += 1
                    continue
                
                # First extract starting chapter
                print(f"\n--- Extracting first part: Surah {start_chapter} from verse {start_verse} to end ---")
                success1 = extract_verses_with_counter(
                    pdf_path,
                    start_chapter,
                    start_verse,
                    None,  # Extract all verses from starting verse to end of chapter
                    output_dir,
                    chapter_start_page=start_chapter_page
                )
                
                # Then extract ending chapter
                print(f"\n--- Extracting second part: Surah {end_chapter} from start to verse {end_verse} ---")
                success2 = extract_verses_with_counter(
                    pdf_path,
                    end_chapter,
                    1,  # Start from beginning of chapter
                    end_verse,
                    output_dir,
                    chapter_start_page=end_chapter_page
                )
                
                if success1 and success2:
                    success_count += 1
                else:
                    failure_count += 1
        
        # Print summary
        print("\n============ EXTRACTION COMPLETE ============")
        output_files = [f for f in os.listdir(output_dir) if f.startswith("quran_") and f.endswith(".png")]
        print(f"Successfully processed {success_count} API pages, failed on {failure_count} pages.")
        print(f"Found {len(output_files)} output image files in {output_dir}")
        print(f"Surah pages found: {surah_pages}")
        print(f"Images have been saved to: {output_dir}")
        print("\nIf the extraction results are not correct, try:")
        print("1. Open the PDF manually and check the exact page numbers of your target surahs")
        print("2. Use the script with manually specified page ranges instead of API detection")
        print("3. Check your internet connection if API requests are failing")
    
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error during extraction: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nQuran extraction completed") 