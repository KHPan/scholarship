import json
import os
from urllib.parse import urljoin
import mimetypes
import time

import requests
from bs4 import BeautifulSoup

import jsonlines
import magic
from markdownify import markdownify

with open("3-1.json", "r", encoding="utf-8") as f:
	ids = json.load(f)["ids"]

mime_detector = magic.Magic(mime=True)
if not os.path.exists("temp"):
	os.mkdir("temp")
for id in ids:
	url = f"https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id={id}"
	resp = requests.get(url)
	soup = BeautifulSoup(resp.text, "lxml")
	table = soup.find("table", class_="blank-line-half")

	filenames = []
	file_information = []
	all_files_cnt = 0
	fail_filenames = []
	for link in table.find_all("a", href=True):
		href = link.get("href")
		if not href or href.startswith('#'):
			continue
		all_files_cnt += 1
		file_url = urljoin(url, href)
		print(f"Downloading {id}-{link.getText().strip()}: {file_url}...")
		filename = f"temp/{id}_{len(filenames)}"
		try:
			with requests.get(file_url, stream=True, timeout=20) as r:
				r.raise_for_status()  # 如果請求失敗 (如 404)，會拋出異常
				# 以二進位寫入模式打開檔案
				with open(filename, 'wb') as f:
					# 分塊寫入，避免一次性將大檔案載入記憶體
					for chunk in r.iter_content(chunk_size=8192):
						f.write(chunk)
		except Exception as e:
			continue
		mime_type = mime_detector.from_file(filename)
		extension = mimetypes.guess_extension(mime_type)
		os.rename(filename, f"{filename}{extension}")
		filename = f"{filename}{extension}"
		if extension in (".htm", ".html"):
			with open(filename, "r", encoding="utf-8") as f:
				html_content = f.read()
			markdown_content = markdownify(html_content)
			base_name = os.path.splitext(os.path.basename(filename))[0]
			output_md = os.path.join("temp", f"{base_name}.md.txt")
			with open(output_md, "w", encoding="utf-8") as f:
				f.write(markdown_content)
			filename = output_md
		file_information.append(f"顯示為「{link.getText().strip()}」"
						f"網址為「{file_url}」的檔案存在於「{filename}」")
		filenames.append(filename)