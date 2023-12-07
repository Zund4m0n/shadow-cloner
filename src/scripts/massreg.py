'''
Mass URL Generator / Validator.

Usage examples:
- GigaFile
   massregex "https://xgf\.nu/[a-zA-Z0-9]{5}?" -l 1000 -t 5 -i 3 -o gigafile.txt

- PayPay
   massregex "https://xgf\.nu/[a-zA-Z0-9]{4}" -l 1000 -t 5 -i 3 -o paypay.txt

- PayPal
   massregex "[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}" -l 1000 -t 5 -i 3 -o paypay.txt

- Gist
- githack
- Pastebin "[a-zA-Z0-9]{8}"
- firestorage
- kozutumi
- iFixit
    massreg -r 'https://www\.ifixit\.com/GuidePDF/link/\d+/en' -l 6 --interval 0


Ref.
- URL: ^((http|https|ftp):\/\/)?([a-zA-Z0-9.-]+(\.[a-zA-Z]{2,6})+)((\/|\?|#)[^\s]*)?$

'''

import argparse
import exrex
from tqdm import tqdm
import http.client
import httpx
import asyncio
import tempfile
import os
import re
import yaml
from datetime import datetime


async def generate_ord(regex, limit):
    print(f'Count: {exrex.count(regex, limit=limit)}')
    print(f'Range limit: {limit}')
    return '\n'.join(exrex.generate(regex, limit=limit))

async def generate_rand(regex, limit):
    return exrex.getone(regex, limit=limit)

async def generate_urls(regex, output_file, count, limit, sort, interval):
    try:
        with open(output_file, "w") as file:

            if sort == 'natural':
                url = await generate_ord(regex, limit)
                file.write(url + "\n")
            else:
                for _ in tqdm(range(count), desc="Generating"):
                    try:
                        url = await generate_rand(regex, limit)
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

async def check_valid_urls(input_file, output_file, interval, timeout):
    try:
        with open(input_file, "r") as input_file, open(output_file, "w") as output_file:
            urls = input_file.readlines()
            for i, url in tqdm(enumerate(urls, start=1), desc="Checking Validity"):
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
                        yaml.dump({i: [log_entry]}, output_file, default_flow_style=False)
                except httpx.RequestError as e:
                    if hasattr(e, "response") and e.response is not None:
                        print(f"Error while checking {url}: {e.response.status_code}", end="\r")
                        log_entry = {
                            "error": f"Error while checking {url}: {e.response.status_code}",
                            "url": url
                        }
                        yaml.dump({i: [log_entry]}, output_file, default_flow_style=False)
                    else:
                        print(f"Error while checking {url}: {e}", end="\r")
                        log_entry = {
                            "error": f"Error while checking {url}: {e}",
                            "url": url
                        }
                        yaml.dump({i: [log_entry]}, output_file, default_flow_style=False)
                except Exception as e:
                    print(f"Unknown error while checking {url}: {e}", end="\r")
                    log_entry = {
                        "error": f"Unknown error while checking {url}: {e}",
                        "url": url
                    }
                    yaml.dump({i: [log_entry]}, output_file, default_flow_style=False)
                await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print("\nGeneration and checking interrupted. Partial results saved.", end="\r")
    except Exception as e:
        print(f"Unknown error: {e}", end="\r")

def match_urls(input_file, regex):
    try:
        with open(input_file, "r") as file:
            urls = file.readlines()
            for url in tqdm(urls, desc="Matching URLs"):
                url = url.strip()
                if re.match(regex, url):
                    print(f"{url} matches the regex.")
                else:
                    print(f"{url} does not match the regex.")
    except KeyboardInterrupt:
        print("\nMatching interrupted.")

def custom_traceroute(url):
    # Placeholder for custom traceroute logic
    print(f"Traceroute for {url}")

async def main():
    parser = argparse.ArgumentParser(description="Generate URLs with specified regex pattern and check their validity.")
    parser.add_argument("-i", "--input", help="Input file for checking validity")
    parser.add_argument("-o", "--output", default="output.txt", help="Output file for generated URLs (default: output.txt)")
    parser.add_argument("-r", "--regex", default="https://www\.example\.com/\d{7}", help="Regular expression pattern for generating random strings")
    parser.add_argument("-c", "--count", type=int, default=10, help="Max number of urls (default: 10) [WIP: only works in random]")
    parser.add_argument("-l", "--limit", type=int, default=1, help="Max string length range limit (default: 1)")
    parser.add_argument("-t", "--timeout", type=int, default=5, help="Timeout for HTTP requests (default: 5 seconds)")
    parser.add_argument("--interval", type=int, default=1, help="Interval between requests (default: 1 second)")
    parser.add_argument("-m", "--mode", nargs="+", choices=["generate", "check", "match"], default=["generate"], help="Mode: generate, check, or match (default: generate)")
    parser.add_argument("-s", "--sort", nargs="+", choices=["natural", "asc", "desc"], default=["random"], help="Sort: generate, asc, or desc (default: random)")

    args = parser.parse_args()

    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_file = f"{log_dir}/{timestamp}.yaml"

    if "generate" in args.mode:
        temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)

        await generate_urls(args.regex, temp_file.name, args.count, args.limit, args.sort, args.interval)

        print(f"Generated URLs are saved to: {temp_file.name}")

        # Clean up the temporary file
        temp_file.close()
        # os.remove(temp_file.name)

    if "check" in args.mode:
        await check_valid_urls(args.input, log_file, args.interval, args.timeout)

    if "match" in args.mode:
        match_urls(args.output, args.regex)

    # Perform custom traceroute logic
    # with open(args.output, "r") as file:
    #     urls = file.readlines()
    #     for url in tqdm(urls, desc="Traceroute"):
    #         custom_traceroute(url.strip())

if __name__ == "__main__":
    asyncio.run(main())
