import time

from google import genai

import gemi_client

prompt = """
將附檔內容所有文字(包括文字與圖中文字)完整轉換成 Markdown 格式
"""

class AIException(Exception):
	def __init__(self, messages: list[str]):
		self.messages = messages
		super().__init__("\n".join(messages))

def convert(filename: str, is_show: bool = True) -> str:
	ret = None
	run_cnt = 0
	err_msg = []
	while ret is None and run_cnt < 5:
		if run_cnt > 0:
			if is_show:
				print(f"轉檔：等待 {gemi_client.wait_seconds} 秒後重試...")
			time.sleep(gemi_client.wait_seconds)
		client = gemi_client.get_client()
		if is_show:
			print(f"轉檔：上傳檔案{filename}...")
		file = client.files.upload(file=filename)
		run_cnt += 1
		if is_show:
			print("轉檔：運行 Gemini 進行轉檔...")
		try:
			response = client.models.generate_content(
				model=gemi_client.model,
				contents=[file, prompt],
			)
		except genai.errors.ServerError as e:
			err_msg.append(f"Gemini Server error: {e}")
			print(f"轉檔：Gemini Server error: {e}")
			continue
		except Exception as e:
			err_msg.append(f"Gemini unexpected error: {e}")
			print(f"轉檔：Gemini unexpected error: {e}")
			continue
		ret = response.text
	if ret is None:
		raise AIException(err_msg)
	return ret

if __name__ == "__main__":
	filename = "temp/7455_1.pdf"
	text = convert(filename)
	with open("temp/7455_1.md", "w", encoding="utf-8") as f:
		f.write(text)