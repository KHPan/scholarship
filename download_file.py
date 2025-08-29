import os
import mimetypes

import requests
import magic

_mime_detector = magic.Magic(mime=True)

class DownloadFailException(Exception):
	pass

def download(url: str, filename_without_extension: str) -> str:
	try:
		with requests.get(url, stream=True, timeout=20) as r:
			r.raise_for_status()  # 如果請求失敗 (如 404)，會拋出異常
			# 以二進位寫入模式打開檔案
			with open(filename_without_extension, 'wb') as f:
				# 分塊寫入，避免一次性將大檔案載入記憶體
				for chunk in r.iter_content(chunk_size=8192):
					f.write(chunk)
	except Exception as e:
		raise DownloadFailException() from e
	mime_type = _mime_detector.from_file(filename_without_extension)
	extension = mimetypes.guess_extension(mime_type)
	filename = f"{filename_without_extension}{extension}"
	os.rename(filename_without_extension, filename)
	return filename