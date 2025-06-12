# Nanashi_Downloader.py
import os
import re
import subprocess
import requests
import math
import multiprocessing
import urllib.parse
import cloudscraper
import pyperclip
import time
from tqdm import tqdm
from termcolor import colored
from bs4 import BeautifulSoup

DOWNLOAD_PATH = "T:\GAMEESSS"
CHUNK_COUNT = 8

# LOG
log = lambda prefix, msg, color: print(colored(f"[{prefix}] {msg}", color))
info = lambda msg: log("INFO", msg, "cyan")
success = lambda msg: log("SUCCESS", msg, "green")
error = lambda msg: log("ERROR", msg, "red")
action = lambda msg: log("ACTION", msg, "magenta")

# GOOGLE DRIVE - BYPASS
def get_gdrive_direct_link(file_id):
    """Get direct download link for Google Drive file with advanced bypass"""
    session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        direct_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t"
        test_response = session.head(direct_url, headers=headers, allow_redirects=True, timeout=10)
        content_type = test_response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type and test_response.status_code == 200:
            info("Using direct usercontent URL")
            return direct_url
    except:
        pass
    
    URL = "https://docs.google.com/uc?export=download"
    params = {'id': file_id}
    
    try:
        response = session.get(URL, params=params, headers=headers, timeout=15)
        response_text = response.text[:2000]  # Only check first 2000 chars for performance
        
        if any(html_indicator in response_text.lower() for html_indicator in ['<html', '<!doctype', '<head>', 'virus-scan-warning']):
            info("Detected HTML response, extracting bypass URL...")
            patterns = [
                r'href="(https://[^"]*uc\?[^"]*export=download[^"]*)"',
                r'href="(/uc\?[^"]*export=download[^"]*)"',
                r'"downloadUrl":"([^"]*)"',
                r'href="(https://drive\.usercontent\.google\.com/download[^"]*)"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response_text)
                if match:
                    download_url = match.group(1)
                    if download_url.startswith('/'):
                        download_url = "https://docs.google.com" + download_url
                    info(f"Found bypass URL using pattern matching")
                    return download_url
            
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    confirm_url = f"{URL}?id={file_id}&confirm={value}"
                    info("Using cookie-based confirm token")
                    return confirm_url
            
            try:
                soup = BeautifulSoup(response_text, 'html.parser')
                
                form = soup.find('form')
                if form and form.get('action'):
                    action_url = form.get('action')
                    if not action_url.startswith('http'):
                        action_url = "https://docs.google.com" + action_url
                    info("Found download URL in form action")
                    return action_url
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'export=download' in href or 'uc?' in href:
                        if not href.startswith('http'):
                            href = "https://docs.google.com" + href
                        info("Found download URL in page links")
                        return href
            except:
                pass
        
        else:
            return response.url
            
    except Exception as e:
        error(f"Error in bypass attempt: {str(e)}")
    
    fallback_urls = [
        f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
        f"https://docs.google.com/uc?export=download&id={file_id}&confirm=1",
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
    ]
    
    for url in fallback_urls:
        try:
            test_resp = session.head(url, headers=headers, allow_redirects=True, timeout=5)
            content_type = test_resp.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and test_resp.status_code == 200:
                info("Using fallback URL")
                return url
        except:
            continue
    
    return fallback_urls[0]

def gdrive_download(link):
    """Download from Google Drive with bypass"""
    info("Google Drive download...")
    
    file_id = None
    patterns = [
        r"/d/([\w-]+)",  # /file/d/FILE_ID/view
        r"id=([\w-]+)",  # ?id=FILE_ID
        r"/open\?id=([\w-]+)"  # /open?id=FILE_ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            file_id = match.group(1)
            break
    
    if not file_id:
        error("Invalid Google Drive link - cannot extract file ID.")
        return
    
    info(f"Extracted file ID: {file_id}")
    
    download_methods = [
        ("Enhanced bypass", lambda: enhanced_gdrive_download(file_id)),
        ("Aria2c direct", lambda: aria2c_gdrive_download(file_id)),
        ("Wget bypass", lambda: wget_gdrive_download(file_id)),
    ]
    
    for method_name, method_func in download_methods:
        try:
            info(f"Trying {method_name}...")
            if method_func():
                return
        except Exception as e:
            error(f"{method_name} failed: {str(e)}")
    
    error("All download methods failed!")

def enhanced_gdrive_download(file_id):
    """Enhanced download method with progress display"""
    direct_link = get_gdrive_direct_link(file_id)
    if not direct_link:
        return False
    
    info(f"Testing direct link: {direct_link[:50]}...")
    
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        test_headers = headers.copy()
        test_headers['Range'] = 'bytes=0-1023'
        
        test_response = session.get(direct_link, headers=test_headers, timeout=10)
        
        content_type = test_response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type or b'<html' in test_response.content[:100].lower():
            info("Direct link still returns HTML, skipping...")
            return False
        
        filename, size = get_file_info(direct_link)
        if size > 0:
            action(f"File: {filename} | Size: {size / (1024**2):.2f} MB")
            gdrive_progress_download(direct_link, filename, size)
            return True
        else:
            return False
            
    except Exception as e:
        error(f"Enhanced method error: {str(e)}")
        return False

def aria2c_gdrive_download(file_id):
    """Download using aria2c with progress display"""
    try:
        urls = [
            f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t",
            f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
            f"https://docs.google.com/uc?export=download&id={file_id}&confirm=1"
        ]
        
        for i, url in enumerate(urls):
            try:
                info(f"🔄 Trying aria2c method {i+1}/3...")
                filename = f"gdrive_file_{file_id}"
                
                cmd = [
                    'aria2c',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    '--header=Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    '--header=Accept-Language: en-US,en;q=0.5',
                    '--header=Accept-Encoding: gzip, deflate',
                    '--header=Connection: keep-alive',
                    '--max-tries=3',
                    '--retry-wait=2',
                    '--timeout=60',
                    '--connect-timeout=10',
                    '--summary-interval=1',
                    '--console-log-level=info',
                    '--download-result=full',
                    '-x', '16',
                    '-s', '16',
                    '-o', filename,
                    url,
                    '-d', DOWNLOAD_PATH
                ]
                
                info(f"🚀 Starting download with aria2c...")
                info(f"📁 Saving to: {os.path.join(DOWNLOAD_PATH, filename)}")
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    universal_newlines=True,
                    bufsize=1
                )
                
                download_info = {'speed': '0 B/s', 'progress': '0%', 'eta': 'Unknown'}
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        
                        
                        if '[#' in line and ']' in line:
                            
                            try:
                                
                                speed_match = re.search(r'DL:([0-9.]+[KMGT]?i?B)', line)
                                if speed_match:
                                    download_info['speed'] = speed_match.group(1) + '/s'
                                
                                
                                percent_match = re.search(r'\(([0-9]+)%\)', line)
                                if percent_match:
                                    download_info['progress'] = percent_match.group(1) + '%'
                                
                                
                                eta_match = re.search(r'ETA:([0-9smh]+)', line)
                                if eta_match:
                                    download_info['eta'] = eta_match.group(1)
                                
                                
                                print(f"\r🚀 Progress: {download_info['progress']} | Speed: {download_info['speed']} | ETA: {download_info['eta']}", end='', flush=True)
                            except:
                                pass
                        
                        
                        elif any(keyword in line.lower() for keyword in ['download complete', 'error', 'failed']):
                            print(f"\n{line}")
                
                return_code = process.poll()
                print()  
                file_path = os.path.join(DOWNLOAD_PATH, filename)
                if os.path.exists(file_path) and return_code == 0:
                    with open(file_path, 'rb') as f:
                        first_bytes = f.read(1024).lower()
                        if b'<html' in first_bytes or b'<!doctype' in first_bytes:
                            info("❌ Downloaded file is HTML, trying next method...")
                            os.remove(file_path)
                            continue
                    
                    file_size = os.path.getsize(file_path)
                    file_size_mb = file_size / (1024 * 1024)
                    
                    success(f"✅ Download completed successfully!")
                    info(f"📊 File: {filename}")
                    info(f"📊 Size: {file_size_mb:.2f} MB")
                    info(f"📊 Saved to: {file_path}")
                    return True
                else:
                    error(f"❌ Download failed with return code: {return_code}")
                    
            except Exception as e:
                error(f"Aria2c attempt {i+1} failed: {str(e)}")
                continue
        
        return False
        
    except Exception as e:
        error(f"Aria2c method failed: {str(e)}")
        return False

def wget_gdrive_download(file_id):
    """Download using wget with Google Drive bypass"""
    try:
        info("Trying wget method...")
        filename = f"gdrive_file_{file_id}"
        url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t"
        
        cmd = [
            'wget',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header=Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '--no-check-certificate',
            '--timeout=30',
            '--tries=3',
            '--continue',
            '-O', os.path.join(DOWNLOAD_PATH, filename),
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        file_path = os.path.join(DOWNLOAD_PATH, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                first_bytes = f.read(1024).lower()
                if b'<html' in first_bytes or b'<!doctype' in first_bytes:
                    info("Wget downloaded HTML, method failed")
                    os.remove(file_path)
                    return False
            
            success(f"Wget download successful: {filename}")
            return True
        
        return False
        
    except Exception as e:
        error(f"Wget method failed: {str(e)}")
        return False

# MEGA
def mega_download(link):
    info("Mega.nz download...")
    cmd = f"megadl '{link}' --path {DOWNLOAD_PATH}"
    subprocess.run(cmd, shell=True)
    success("Mega download done.")

# MEDIAFIRE
def mediafire_direct(link):
    scraper = cloudscraper.create_scraper()
    page = scraper.get(link).text
    match = re.search(r'href=\"(https://download[^\"]+)', page)
    if match:
        return match.group(1)
    return None

def mediafire_download(link):
    info("MediaFire download...")
    direct_link = mediafire_direct(link)
    if not direct_link:
        error("Can't resolve Mediafire link.")
        return
    filename, size = get_file_info(direct_link)
    action(f"File: {filename} | Size: {size / (1024**2):.2f} MB")
    turbo_download(direct_link, filename, size)

# ONEDRIVE
def onedrive_download(link):
    info("OneDrive download...")
    name = link.split("/")[-1].split("?")[0]
    if not name or name == "":
        name = f"onedrive_file_{int(time.time())}"
    cmd = f'aria2c -x 16 -s 16 -o "{name}" "{link}" -d {DOWNLOAD_PATH}'
    subprocess.run(cmd, shell=True)
    success(f"Saved: {os.path.join(DOWNLOAD_PATH, name)}")

# DIRECT LINK
def direct_download(link):
    info("Direct download...")
    name = link.split("/")[-1].split("?")[0]
    if not name or name == "":
        name = f"direct_file_{int(time.time())}"
    cmd = f'aria2c -x 16 -s 16 -o "{name}" "{link}" -d {DOWNLOAD_PATH}'
    subprocess.run(cmd, shell=True)
    success(f"Saved: {os.path.join(DOWNLOAD_PATH, name)}")

# MULTI-THREAD DOWNLOAD CORE
def get_file_info(url):
    """Get filename and size, with better error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        r = requests.head(url, headers=headers, allow_redirects=True, timeout=30)
        size = int(r.headers.get('Content-Length', 0))
        
        filename = "downloaded_file"
        
        if 'Content-Disposition' in r.headers:
            cd = r.headers['Content-Disposition']
            filename_match = re.search(r'filename[*]?=([^;]+)', cd)
            if filename_match:
                filename = filename_match.group(1).strip('"\'')
        
        if filename == "downloaded_file":
            filename = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
            if not filename or filename == "uc":
                filename = f"download_{int(time.time())}"
        
        return filename, size
        
    except Exception as e:
        error(f"Failed to get file info: {str(e)}")
        return f"download_{int(time.time())}", 0

def download_part(url, start, end, part_num, filename):
    """Download a part of the file"""
    try:
        headers = {
            'Range': f'bytes={start}-{end}', 
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get(url, headers=headers, stream=True, timeout=60)
        
        part_path = os.path.join(DOWNLOAD_PATH, f"{filename}.part{part_num}")
        
        with open(part_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
        
        info(f"Part {part_num} downloaded successfully")
        
    except Exception as e:
        error(f"Failed to download part {part_num}: {str(e)}")

def turbo_download(url, filename, size):
    """Multi-threaded download with progress tracking"""
    info(f"🚀 Starting download with {CHUNK_COUNT} threads...")
    
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    
    if 'drive.google.com' in url or 'drive.usercontent.google.com' in url:
        return gdrive_progress_download(url, filename, size)
    
    chunk_size = math.ceil(size / CHUNK_COUNT)
    processes = []
    start_time = time.time()
    
    info(f"📊 File: {filename}")
    info(f"📊 Size: {size / (1024**2):.2f} MB")
    info(f"📊 Threads: {CHUNK_COUNT}")
    
    for i in range(CHUNK_COUNT):
        start = i * chunk_size
        end = min(start + chunk_size - 1, size - 1)
        
        p = multiprocessing.Process(
            target=download_part, 
            args=(url, start, end, i, filename)
        )
        p.start()
        processes.append(p)
    
    total_downloaded = 0
    while any(p.is_alive() for p in processes):
        current_downloaded = 0
        for i in range(CHUNK_COUNT):
            part_path = os.path.join(DOWNLOAD_PATH, f"{filename}.part{i}")
            if os.path.exists(part_path):
                current_downloaded += os.path.getsize(part_path)
        
        if current_downloaded > total_downloaded:
            total_downloaded = current_downloaded
            elapsed = time.time() - start_time
            speed = total_downloaded / elapsed if elapsed > 0 else 0
            speed_mb = speed / (1024 * 1024)
            progress = (total_downloaded / size) * 100 if size > 0 else 0
            
            print(f"\r🚀 Progress: {progress:.1f}% | Speed: {speed_mb:.2f} MB/s | Downloaded: {total_downloaded/(1024**2):.1f}/{size/(1024**2):.1f} MB", end='', flush=True)
        
        time.sleep(0.5)
    
    for p in processes:
        p.join()
    
    print()
    
    if merge_parts(filename):
        total_time = time.time() - start_time
        avg_speed_mb = (size / (1024**2)) / total_time if total_time > 0 else 0
        
        success(f"✅ Download completed!")
        info(f"📊 Time: {total_time:.1f} seconds")
        info(f"📊 Average Speed: {avg_speed_mb:.2f} MB/s")
        info(f"📊 Saved to: {os.path.join(DOWNLOAD_PATH, filename)}")
    else:
        error("❌ Download failed during merging")

def gdrive_progress_download(url, filename, total_size):
    """Download with detailed progress display and speed monitoring"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        file_path = os.path.join(DOWNLOAD_PATH, filename)
        
        # Initialize progress tracking
        downloaded = 0
        start_time = time.time()
        last_update = start_time
        chunk_size = 8192
        
        # Create progress bar
        progress_bar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=f"📥 {filename[:30]}",
            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
        )
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress_bar.update(len(chunk))
                    current_time = time.time()
                    if current_time - last_update >= 1.0:
                        elapsed = current_time - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        
                        percent = (downloaded / total_size) * 100 if total_size > 0 else 0
                        speed_mb = speed / (1024 * 1024)
                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        
                        print(f"\r🚀 Progress: {percent:.1f}% | Speed: {speed_mb:.2f} MB/s | Downloaded: {downloaded_mb:.1f}/{total_mb:.1f} MB", end='', flush=True)
                        
                        last_update = current_time
        
        progress_bar.close()
        print()  
        
        total_time = time.time() - start_time
        avg_speed = downloaded / total_time if total_time > 0 else 0
        avg_speed_mb = avg_speed / (1024 * 1024)
        
        success(f"✅ Download completed!")
        info(f"📊 File: {filename}")
        info(f"📊 Size: {total_mb:.2f} MB")
        info(f"📊 Time: {total_time:.1f} seconds")
        info(f"📊 Average Speed: {avg_speed_mb:.2f} MB/s")
        info(f"📊 Saved to: {file_path}")
        
        return True
        
    except Exception as e:
        error(f"Progress download failed: {str(e)}")
        return False

# AUTO DETECT
def auto_download(link):
    """Auto-detect link type and download"""
    if not link or link.strip() == "":
        error("Empty link provided")
        return
        
    link = link.strip()
    info(f"Processing link: {link}")
    
    if "drive.google.com" in link:
        gdrive_download(link)
    elif "mega.nz" in link or "mega.co.nz" in link:
        mega_download(link)
    elif "mediafire.com" in link:
        mediafire_download(link)
    elif "1drv.ms" in link or "sharepoint.com" in link:
        onedrive_download(link)
    elif link.startswith(("http://", "https://")):
        direct_download(link)
    else:
        error("Unsupported link type")

# MENU
def menu():
    """Main menu interface"""
    while True:
        os.system("clear" if os.name == "posix" else "cls")
        print(colored("\n🚀 Nanashi Downloader V1\n", "yellow", attrs=["bold"]))
        print("1️⃣ Paste link manually")
        print("2️⃣ Read from clipboard")
        print("3️⃣ Read list from file")
        print("4️⃣ Settings")
        print("5️⃣ Exit")
        
        choice = input("\n👉 Your choice: ").strip()

        if choice == '1':
            link = input("📎 Enter link: ").strip()
            if link:
                auto_download(link)
                input("\nPress Enter to continue...")
            else:
                error("No link provided")
                
        elif choice == '2':
            try:
                link = pyperclip.paste()
                info(f"Clipboard: {link}")
                if link:
                    auto_download(link)
                else:
                    error("Clipboard is empty")
                input("\nPress Enter to continue...")
            except Exception as e:
                error(f"Clipboard read failed: {str(e)}")
                input("\nPress Enter to continue...")
                
        elif choice == '3':
            filename = input("📄 File name: ").strip()
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as file:
                        links = [line.strip() for line in file if line.strip()]
                        info(f"Found {len(links)} links in file")
                        for i, link in enumerate(links, 1):
                            info(f"Processing link {i}/{len(links)}")
                            auto_download(link)
                    success("Batch download completed")
                except Exception as e:
                    error(f"Failed to process file: {str(e)}")
                input("\nPress Enter to continue...")
            else:
                error("File not found")
                input("\nPress Enter to continue...")
                
        elif choice == '4':
            settings_menu()
            
        elif choice == '5':
            success("Goodbye! 👋")
            break
            
        else:
            error("Invalid choice")
            input("\nPress Enter to continue...")

def settings_menu():
    """Settings configuration menu"""
    global CHUNK_COUNT, DOWNLOAD_PATH
    
    while True:
        os.system("clear" if os.name == "posix" else "cls")
        print(colored("\n⚙️ SETTINGS ⚙️\n", "yellow", attrs=["bold"]))
        print(f"📁 Download Path: {DOWNLOAD_PATH}")
        print(f"🧵 Thread Count: {CHUNK_COUNT}")
        print("\n1️⃣ Change download path")
        print("2️⃣ Change thread count")
        print("3️⃣ Back to main menu")
        
        choice = input("\n👉 Your choice: ").strip()
        
        if choice == '1':
            new_path = input("📁 Enter new download path: ").strip()
            if new_path and os.path.exists(new_path):
                DOWNLOAD_PATH = new_path
                success(f"Download path changed to: {DOWNLOAD_PATH}")
            else:
                error("Invalid path")
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            try:
                new_count = int(input("🧵 Enter thread count (1-16): ").strip())
                if 1 <= new_count <= 16:
                    CHUNK_COUNT = new_count
                    success(f"Thread count changed to: {CHUNK_COUNT}")
                else:
                    error("Thread count must be between 1 and 16")
            except ValueError:
                error("Invalid number")
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            break
            
        else:
            error("Invalid choice")
            input("\nPress Enter to continue...")

if __name__ == '__main__':
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    
    try:
        menu()
    except KeyboardInterrupt:
        print("\n")
        success("Program interrupted by user. Goodbye! 👋")
    except Exception as e:
        error(f"Unexpected error: {str(e)}")
        input("\nPress Enter to exit...")