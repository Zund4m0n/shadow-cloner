'''
Mass URL Generator / Checker.

Usage examples:

- GigaFile
    massreg -p "https://xgf\.nu/[a-zA-Z0-9]{5}?" -m generate

- PayPal
    massreg -p "[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}" -l 1000 -t 5 -i 3 -m generate

- iFixit
    massreg -p 'https://www\.ifixit\.com/GuidePDF/link/\d+/en' -l 6 -i 0 -s natural -m generate
    massreg $INPUT -o ifixit-1.txt -l 1 -i 0

Author: -
License: MIT
'''

import os
import re
import sys
import yaml
import exrex
import httpx
import signal
import asyncio
import argparse
import tempfile
import http.client
from tqdm import tqdm
from datetime import datetime


async def generate_ord(p, limit):
    print(f'Count: {exrex.count(p, limit=limit)}')
    print(f'Range limit: {limit}')
    return '\n'.join(exrex.generate(p, limit=limit))

async def generate_rand(p, limit):
    return exrex.getone(p, limit=limit)

async def generate_urls(p, tmpf, count, limit, sort, interval):
    try:
        with open(tmpf, "w") as file:

            if sort == ['natural']:
                url = await generate_ord(p, limit)
                file.write(url + "\n")
            else:
                for _ in tqdm(range(count), desc="Generating"):
                    try:
                        url = await generate_rand(p, limit)
                        file.write(url + "\n")
                    except Exception as e:
                        print(f"Error generating URL: {e}")
                    await asyncio.sleep(interval)
                    # await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print("\nGeneration interrupted. Partial results saved.")
    except Exception as e:
        print(f"Error during generation: {e}")

async def get_status_message(status_code):
    return http.client.responses.get(status_code, "Unknown Status")

async def check_valid_urls(urls, log, interval, timeout, content_subdir, download):
    try:
        with open(log, "w") as log:
            for i, url in tqdm(enumerate(urls, start=1), desc="Checking Validity", total=len(urls), leave=False):
                url = url.strip()
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.head(url, timeout=timeout)
                        status_message = await get_status_message(response.status_code)
                        print(f"[{response.status_code}]{status_message}: {url}", end="\r")
                        log_entry = {
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "url": url
                        }
                        yaml.dump({i: [log_entry]}, log, default_flow_style=False)

                        # Download contents if specified
                        if download and response.status_code == 200:
                            await download_contents(url, content_subdir)
                except httpx.RequestError as e:
                    if hasattr(e, "response") and e.response is not None:
                        print(f"Error while checking {url}: {e.response.status_code}", end="\r")
                        log_entry = {
                            "error": f"Error while checking {url}: {e.response.status_code}",
                            "url": url
                        }
                        yaml.dump({i: [log_entry]}, log, default_flow_style=False)
                    else:
                        print(f"Error while checking {url}: {e}", end="\r")
                        log_entry = {
                            "error": f"Error while checking {url}: {e}",
                            "url": url
                        }
                        yaml.dump({i: [log_entry]}, log, default_flow_style=False)
                except Exception as e:
                    print(f"Unknown error while checking {url}: {e}", end="\r")
                    log_entry = {
                        "error": f"Unknown error while checking {url}: {e}",
                        "url": url
                    }
                    yaml.dump({i: [log_entry]}, log, default_flow_style=False)
                await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print("\nGeneration and checking interrupted. Partial results saved.")
    except Exception as e:
        print(f"Error during checking: {e}")
    finally:
        print(f'Saved at: {log.name}')

def match_urls(input_path, pattern):
    try:
        with open(input_path, "r") as file:
            urls = file.readlines()
            for url in tqdm(urls, desc="Matching URLs"):
                url = url.strip()
                if re.match(pattern, url):
                    print(f"{url} matches the regex.")
                else:
                    print(f"{url} does not match the regex.")
    except KeyboardInterrupt:
        print("\nMatching interrupted.")

def custom_traceroute(url):
    # Placeholder for custom traceroute logic
    print(f"Traceroute for {url}")

async def download_contents(url, output_folder):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                # Create a timestamped folder to save contents
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                save_folder = os.path.join(output_folder, f"contents/{timestamp}")
                os.makedirs(save_folder, exist_ok=True)

                # Save contents to a file
                content_filename = os.path.join(save_folder, "content.html")
                with open(content_filename, "wb") as content_file:
                    content_file.write(response.content)

                print(f"Contents downloaded and saved to: {content_filename}")
            else:
                print(f"Failed to download contents from {url}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading contents from {url}: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Generate URLs with specified regex pattern and check their validity.")
    parser.add_argument('input_path', nargs='*', help='Input path for URLs. If not provided, read from stdin.')
    parser.add_argument("-o", "--output_path", default=None, help="Output path")
    parser.add_argument("-p", "--pattern", default="https://www\.example\.com/\d{7}", help="Regular expression pattern for generating random strings")
    parser.add_argument("-c", "--count", type=int, default=10, help="Max number of urls (default: 10) [WIP: only works in random]")
    parser.add_argument("-l", "--limit", type=int, default=1, help="Max string length range limit (default: 1)")
    parser.add_argument("-t", "--timeout", type=int, default=5, help="Timeout for HTTP requests (default: 5 seconds)")
    parser.add_argument("-I", "--interval", type=int, default=1, help="Interval between requests (default: 1 second)")
    parser.add_argument("-m", "--mode", nargs=1, choices=["check", "generate", "match"], default=["check"], help="Mode: generate, check, or match (default: generate)")
    parser.add_argument("-s", "--sort", nargs="+", choices=["natural", "asc", "desc","random"], default=["random"], help="Sort: generate, asc, or desc (default: random)")
    parser.add_argument("-d", "--download", action="store_true", help="Enable downloading contents for valid URLs (default: False)")

    args = parser.parse_args()
    temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    timestamp = datetime.now().isoformat(timespec='auto')

    if "check" in args.mode:
        log_dir = 'log'
        content_dir = "contents"
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(content_dir, exist_ok=True)
        log_file = f"{log_dir}/{timestamp}.yaml"
        content_subdir = f"{content_dir}/{timestamp}"
        if not args.input_path:
            urls = sys.stdin.read().splitlines()
        else:
            urls = args.input_path
        await check_valid_urls(urls, args.output_path, args.interval, args.timeout, content_subdir, args.download)

    if "generate" in args.mode:
        await generate_urls(args.pattern, temp_file.name, args.count, args.limit, args.sort, args.interval)
        print(f"Generated URLs are saved to: {temp_file.name}")
        temp_file.close()
        # os.remove(temp_file.name)

    if "match" in args.mode:
        match_urls(args.input_path, args.pattern)

    # Perform custom traceroute logic
    # with open(args.output_path, "r") as file:
    #     urls = file.readlines()
    #     for url in tqdm(urls, desc="Traceroute"):
    #         custom_traceroute(url.strip())

if __name__ == "__main__":
    asyncio.run(main())
