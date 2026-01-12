"""
gamebanana.py

Provides a `fetch_mod_from_url(url)` function that returns
(meta, img_url, files) where files is a list of {name, description, download_url}.

Strategy:
 - Try API endpoints (v11 then fallback) with conservative `fields`.
 - If API provides file info, normalize and return.
 - Otherwise scrape public mod page HTML for direct archive links (.zip,.rar,.7z,.pak).
 - Always return normalized results or raise an Exception when nothing found.

This module is dependency-light: it uses `requests` and `re`.
"""

from typing import Tuple, List, Dict, Optional
import requests
import re
import json

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def _parse_gb_url(url: str) -> Tuple[str, str]:
    m = re.search(r"gamebanana\.com/(mods|sounds|skins|guis|gamefiles)/(\d+)", url)
    if not m:
        raise ValueError("Invalid GameBanana URL")
    typ = m.group(1)
    id_ = m.group(2)
    return typ, id_


def _normalize_files_from_api(data) -> List[Dict]:
    # Try to find a files list anywhere in the returned structure
    def find_files(obj):
        if isinstance(obj, dict):
            # direct dict-of-files
            vals = list(obj.values())
            if vals and all(isinstance(v, dict) for v in vals):
                for v in vals:
                    if any(k.lower().find('download') >= 0 or k.lower().find('url') >= 0 or k.lower().find('file') >= 0 for k in v.keys()):
                        return vals
            for k, v in obj.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    if 'file' in k.lower() or 'files' in k.lower() or 'download' in k.lower():
                        return v
                res = find_files(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for it in obj:
                res = find_files(it)
                if res:
                    return res
        return None

    raw = find_files(data)
    out = []
    if not raw:
        return out
    for f in raw:
        if not isinstance(f, dict):
            continue
        dl = None
        for k, v in f.items():
            if isinstance(k, str) and any(x in k.lower() for x in ('download', 'sdownloadurl', 'url')) and isinstance(v, str):
                dl = v
                break
        if not dl:
            dl = f.get('_sDownloadUrl') or f.get('DownloadUrl') or f.get('downloadUrl') or f.get('url') or f.get('file')
        if isinstance(dl, dict):
            # try to pull string urls
            for kk, vv in dl.items():
                if isinstance(vv, str) and vv.lower().startswith('http'):
                    dl = vv
                    break
        name = f.get('_sFile') or f.get('sFile') or f.get('file') or f.get('name') or (dl.split('/')[-1] if isinstance(dl, str) else None)
        desc = f.get('_sDescription') or f.get('description') or ''
        if dl:
            out.append({'name': name, 'description': desc, 'download_url': dl})
    return out


def _scrape_html_for_files(page_url: str, html: str) -> List[Dict]:
    found = []
    # absolute archive URLs
    abs_urls = re.findall(r'https?://[^"\'\s>]+\.(?:zip|rar|7z|pak)(?:\?[^"\'\s>]*)?', html, flags=re.I)
    for u in abs_urls:
        found.append({'name': u.split('/')[-1].split('?')[0], 'description': '', 'download_url': u})
    # relative hrefs
    rel_urls = re.findall(r'href=["\']([^"\']+\.(?:zip|rar|7z|pak))(?:["\']|\?)', html, flags=re.I)
    for u in rel_urls:
        if u.startswith('http'):
            full = u
        else:
            full = requests.compat.urljoin(page_url, u)
        found.append({'name': full.split('/')[-1].split('?')[0], 'description': '', 'download_url': full})
    # search scripts for embedded JSON-like download fields
    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.I | re.S)
    for s in script_matches:
        for m in re.finditer(r'"(sDownloadUrl|downloadUrl|_sDownloadUrl|url)"\s*:\s*"([^"]+\.(?:zip|rar|7z|pak)(?:\?[^\"]*)?)"', s, flags=re.I):
            u = m.group(2)
            if not u.startswith('http'):
                u = requests.compat.urljoin(page_url, u)
            found.append({'name': u.split('/')[-1].split('?')[0], 'description': '', 'download_url': u})
        # Additional heuristic: search script text for escaped or protocol-relative URLs
        for s in script_matches:
            # unescape common JS-escaped slashes
            s_un = s.replace('\\/', '/')
            # find https://... patterns inside scripts
            extra = re.findall(r'https?://[^"\'\s>]+\.(?:zip|rar|7z|pak)(?:\?[^"\'\s>]*)?', s_un, flags=re.I)
            for u in extra:
                if u not in [f.get('download_url') for f in found]:
                    found.append({'name': u.split('/')[-1].split('?')[0], 'description': '', 'download_url': u})
            # find protocol-relative URLs like //cdn.example/...zip
            extra2 = re.findall(r'//[^"\'\s>]+\.(?:zip|rar|7z|pak)(?:\?[^"\'\s>]*)?', s_un, flags=re.I)
            for u in extra2:
                full = 'https:' + u
                if full not in [f.get('download_url') for f in found]:
                    found.append({'name': full.split('/')[-1].split('?')[0], 'description': '', 'download_url': full})
    # deduplicate by URL
    seen = set()
    out = []
    for f in found:
        u = f.get('download_url')
        if u and u not in seen:
            out.append(f)
            seen.add(u)
    return out


def fetch_mod_from_url(url: str) -> Tuple[Dict, Optional[str], List[Dict]]:
    """Fetch mod metadata and list of downloadable files for a GameBanana mod URL.

    Returns (meta, img_url, files).
    """
    typ, item_id = _parse_gb_url(url)
    # 1) Prefer the ProfilePage endpoint which the site uses for the mod page (richer, less strict)
    api_data = None
    try:
        profile_url = f"https://gamebanana.com/apiv11/Mod/{item_id}/ProfilePage"
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(profile_url, timeout=12, headers=headers)
        if r.status_code == 200:
            try:
                j = r.json()
            except Exception:
                j = None
            if isinstance(j, dict) and (j.get('_aFiles') or j.get('_sName') or j.get('_aSubmitter')):
                api_data = j
    except Exception:
        api_data = None

    # 2) If ProfilePage didn't return usable data, try the apiv11/Mod endpoint with _csvFields
    if not api_data:
        try:
            api_url = f"https://gamebanana.com/apiv11/Mod/{item_id}"
            params = {"_csvFields": "name,previewMedia,files,submitter"}
            headers = {"User-Agent": USER_AGENT}
            r = requests.get(api_url, params=params, timeout=12, headers=headers)
            if r.status_code == 200:
                try:
                    j = r.json()
                except Exception:
                    j = None
                if isinstance(j, dict) and (j.get('_aFiles') or j.get('_sName') or j.get('_aSubmitter')):
                    api_data = j
        except Exception:
            api_data = None

    # Fallback older endpoints if apiv11 didn't produce usable data
    if not api_data:
        endpoints = [
            'https://api.gamebanana.com/v11/Core/Item/Data',
            'https://api.gamebanana.com/Core/Item/Data',
        ]
        params_options = [
            'name,description,RootCategory().name',
            'name,description',
        ]
        headers = {'Accept': 'application/json'}
        for api in endpoints:
            for fld in params_options:
                try:
                    r = requests.get(api, params={'itemtype': typ.capitalize() if typ else 'Mod', 'itemid': item_id, 'fields': fld}, timeout=12, headers=headers)
                    if r.status_code == 200:
                        try:
                            j = r.json()
                        except Exception:
                            j = None
                        if isinstance(j, dict) and j.get('error'):
                            continue
                        api_data = j
                        break
                except Exception:
                    continue
            if api_data is not None:
                break

    meta = {'name': f'GB_{item_id}', 'description': '', 'version': '1.0', 'author': 'Unknown', 'category': 'Other'}
    img_url = None
    files = []

    if api_data:
        # If apiv11-style data present (keys with underscores), parse directly
        if isinstance(api_data, dict):
            # Unwrap direct fields
            if api_data.get('_sName'):
                meta['name'] = api_data.get('_sName') or meta['name']
            # Prefer the long HTML text field when available
            if api_data.get('_sText'):
                # Convert basic HTML to plaintext: <br>, <li>, <p>, and strip other tags
                raw = api_data.get('_sText') or ''
                # Normalize common tags to newlines
                raw = re.sub(r'(?i)<br\s*/?>', '\n', raw)
                raw = re.sub(r'(?i)</p>', '\n', raw)
                raw = re.sub(r'(?i)<li[^>]*>', '- ', raw)
                # Remove any remaining tags
                plain = re.sub(r'<[^>]+>', '', raw)
                # Collapse multiple blank lines and trim
                plain = re.sub(r'\n\s*\n+', '\n\n', plain).strip()
                if plain:
                    meta['description'] = plain
            elif api_data.get('_sDescription'):
                meta['description'] = api_data.get('_sDescription')
            # submitter
            submit = api_data.get('_aSubmitter') or api_data.get('_aSubmitter')
            if isinstance(submit, dict):
                meta['author'] = submit.get('_sName') or meta['author']
            # preview media may be array
            pm = api_data.get('_aPreviewMedia') or api_data.get('_aPreviewMedia') or api_data.get('_aPreviewMedia')
            if isinstance(pm, list) and pm:
                # try find a URL inside preview media entries
                for entry in pm:
                    if isinstance(entry, dict):
                        # common keys
                        for k in ('_sBaseUrl', '_sFile', '_sUrl', 'sBaseUrl', 'sFile'):
                            if entry.get(k):
                                if k.lower().endswith('url') and isinstance(entry.get(k), str):
                                    img_url = entry.get(k)
                                    break
                        if img_url:
                            break
            # files list
            files = []
            afiles = api_data.get('_aFiles') or api_data.get('_aFiles') or api_data.get('_aFiles')
            if isinstance(afiles, list):
                for f in afiles:
                    if not isinstance(f, dict):
                        continue
                    dl = f.get('_sDownloadUrl') or f.get('_sFile') or f.get('sDownloadUrl') or f.get('downloadUrl') or f.get('url')
                    name = f.get('_sFile') or f.get('_sName') or (dl.split('/')[-1] if isinstance(dl, str) else None)
                    desc = f.get('_sDescription') or f.get('description') or ''
                    if dl:
                        files.append({'name': name, 'description': desc, 'download_url': dl})
            else:
                # fallback to generic normalization
                files = _normalize_files_from_api(api_data)

    # 2) If no files, scrape the public page
    if not files:
        try:
            headers = {'User-Agent': USER_AGENT}
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                html = r.text
                # try og:image and meta tags for image/desc
                og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
                if og_img:
                    img_url = img_url or og_img.group(1)
                meta_title = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
                if meta_title:
                    meta['name'] = meta_title.group(1)
                meta_desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
                if meta_desc:
                    meta['description'] = meta_desc.group(1)
                scraped = _scrape_html_for_files(url, html)
                files = scraped
        except Exception:
            files = []

    # 3) If still no files, send exception
    if not files:
        raise Exception('No downloadable files found')

    return meta, img_url, files
