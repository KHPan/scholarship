from pydantic import BaseModel
import enum
import json
import os
from urllib.parse import urljoin
import time

import requests
from bs4 import BeautifulSoup

import jsonlines
from google import genai
from dotenv import load_dotenv
from markdownify import MarkdownConverter, markdownify
from send2trash import send2trash

import gemi_client
import download_file
import pdf2md
import word2md

class MyMarkdownConvertor(MarkdownConverter):
	def __init__(self, files: dict[str, str]):
		super().__init__(bs4_options={"features": "lxml"})
		self.files = files
	
	def convert_a(self, el, text, parent_tags):
		# print("see href", el.href)
		if el.get("href") in self.files:
			return (f"\n<DOCUMENT title=\"{el.getText().strip()}\">"
					f"{self.files[el.get('href')]}</DOCUMENT>\n")
		else:
			return super().convert_a(el, text, parent_tags)

class Probability(enum.Enum):
	VERY_POSSIBLE = "VERY_POSSIBLE"
	MAYBE_POSSIBLE = "MAYBE_POSSIBLE"
	MAYBE_IMPOSSIBLE = "MAYBE_IMPOSSIBLE"
	VERY_IMPOSSIBLE = "VERY_IMPOSSIBLE"
ProbabilityMap = {
	Probability.VERY_POSSIBLE: 0.9,
	Probability.MAYBE_POSSIBLE: 0.7,
	Probability.MAYBE_IMPOSSIBLE: 0.3,
	Probability.VERY_IMPOSSIBLE: 0.1,
}

class Data(BaseModel):
	probability: Probability
	reason: str
	prize: int
	information_unsatisfied: bool

with open("3-1.json", "r", encoding="utf-8") as f:
	ids = json.load(f)["ids"]

prompt_template = """
獎學金資訊如下(以<DOCUMENT></DOCUMENT>包裹鏈結後的檔案)：
{table}

# 需求內容
以上為一則獎學金的資訊，請根據以下條件，評估我申請此獎學金的可能性，並用繁體中文說明我能或不能的理由，然後給出這個獎學金的獎金，最後檢測我提供的資料是否不足導致難以判斷。
# 我的條件如下：
性別男，台灣人，學校台灣大學，科系資訊工程學系，年級大三，民國94年1月出生，西元2005年1月出生。
無犯罪紀錄，無特殊事蹟，無社團經歷，無工作經歷，無實習經歷，無專利發明，無競賽獲獎，無職業證照。
上個學期(113-2)，GPA為3.94，對照百分制為84，實得學分19，班/系排91，為前59%
上上個學期(113-1)，GPA為4.00，對照百分制為85，實得學分21，班/系排65，為前41%
整個上學年(113學年)，GPA為3.97，對照百分制為84，實得學分40，班/系排78，為前50%
從沒被當過，無休學紀錄，無延畢紀錄，無退學紀錄，無轉學紀錄，無記過，無不良紀錄。
各個學期的操行分數皆為A，百分制為85-89
家庭條件中，家庭無重大事故無重大傷病，非中低或低收入戶，非清寒，家庭年收入約120萬台幣，父母健在
我身體健康，無重大傷病，無身心障礙，家人也無身心障礙
設籍新北永和，設籍20年
我不曾申請助學貸款，這學期並未申請其他獎學金，從未做過志工或社會實踐

**如果獎學金的某些申請條件，在我的個人資訊中找不到對應資料來判斷，請在理由中明確指出資訊不足，在information_unsatisfied中填入True表明資訊不足，並基於現有資訊進行可能性評估。**
"""

already_ids = set()
for filename in ("3-1_output.jsonl", "3-1_no_success.jsonl"):
	try:
		with jsonlines.open(filename, mode="r") as reader:
			for obj in reader:
				already_ids.add(obj["id"])
	except FileNotFoundError:
		pass

if os.path.exists("temp"):
	send2trash("temp")
os.mkdir("temp")

for id in ids:
	if id in already_ids:
		continue
	url = f"https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id={id}"
	resp = requests.get(url)
	soup = BeautifulSoup(resp.text, "lxml")
	table = soup.find("table", class_="blank-line-half")

	files = {}
	all_files_cnt = 0
	fail_filenames = []
	for link in table.find_all("a", href=True):
		href = link.get("href")
		if not href or href.startswith('#') or href.endswith("login.aspx"):
			continue
		all_files_cnt += 1
		file_url = urljoin(url, href)
		print(f"Downloading {id}-{link.getText().strip()}: {file_url}...")
		filename = f"temp/{id}_{all_files_cnt}"
		try:
			filename = download_file.download(file_url, filename)
		except download_file.DownloadFailException as e:
			print(f"\033[91m{link.getText().strip()} 下載失敗，將不納入評估\033[0m")
			fail_filenames.append((None, f"{link.getText().strip()} download failed: {e}"))
			continue
		if filename.split(".")[-1] in ("htm", "html"):
			with open(filename, "r", encoding="utf-8") as f:
				html_content = f.read()
			markdown_content = markdownify(html_content)
		elif filename.split(".")[-1] in (
						"doc", "docx", "fodt", "odt", "rtf", "pptx"):
			print(f"將 {filename} 轉換為MD...")
			try:
				markdown_content = word2md.convert(filename)
			except word2md.MicrosoftException as e:
				print(f"\033[91m{filename} 轉換為MD失敗，將保留原始檔案\033[0m")
				fail_filenames.append((filename, f"word2md conversion failed {e}"))
				continue
		elif filename.split(".")[-1] in ("pdf", "png", "jpg", "jpeg"):
			try:
				markdown_content = pdf2md.convert(filename)
			except pdf2md.AIException as e:
				print(f"\033[91m{filename} 轉換為MD失敗，將保留原始檔案\033[0m")
				fail_filenames.append((filename, f"pdf2md conversion failed {e}"))
				continue
		elif filename.split(".")[-1] in ("txt", "md"):
			with open(filename, "r", encoding="utf-8") as f:
				markdown_content = f.read()
		else:
			print(f"未見的檔案類型 {filename} ，嘗試以word2md開啟...")
			try:
				markdown_content = word2md.convert(filename)
			except word2md.MicrosoftException as e:
				print(f"\033[91m未見檔案類型 {filename} 轉換為MD失敗，將保留原始檔案\033[0m")
				fail_filenames.append((filename, "unknown file type"))
				continue
		files[href] = markdown_content
		# os.remove(filename)

	# print("files", files.keys())

	convertor = MyMarkdownConvertor(files)
	prompt = prompt_template.format(table=convertor.convert_soup(table))
	with open(f"temp/{id}_prompt.md", "w", encoding="utf-8") as f:
		f.write(prompt)

	my_data = None
	run_cnt = 0
	err_msg = []
	while my_data is None and run_cnt < 5:
		if run_cnt > 0:
			print(f"等待 {gemi_client.wait_seconds} 秒後重試...")
			time.sleep(gemi_client.wait_seconds)
		run_cnt += 1
		print(f"Running Gemini for id {id}...")
		client = gemi_client.get_client()
		try:
			response = client.models.generate_content(
				model=gemi_client.model,
				contents=prompt,
				config={
					"response_mime_type": "application/json",
					"response_schema": Data,
				},
			)
		except genai.errors.ServerError as e:
			err_msg.append(f"Gemini Server error: {e}")
			print(f"Gemini Server error: {e}")
			continue
		except Exception as e:
			err_msg.append(f"Gemini unexpected error: {e}")
			print(f"Gemini unexpected error: {e}")
			continue

		# Use the response as a JSON string.
		print(response.text)

		# Use instantiated objects.
		my_data: Data = response.parsed
		if my_data is None:
			err_msg.append("response None")
	
	if my_data is None:
		print(f"\033[91mid: {id} 跑超過五次皆未成功\033[0m")
		with jsonlines.open("3-1_no_success.jsonl", mode="a") as writer:
			writer.write({"id": id, "model": gemi_client.model, "error": err_msg})
		continue

	my_data = my_data.model_dump()
	my_data["id"] = id
	my_data["probability"] = ProbabilityMap[my_data["probability"]]
	my_data["all_files_cnt"] = all_files_cnt
	my_data["available_files"] = list(files.keys())
	my_data["failed_files"] = fail_filenames
	my_data["model"] = gemi_client.model
	with jsonlines.open("3-1_output.jsonl", mode="a") as writer:
		writer.write(dict(my_data))