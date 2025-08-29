import os
import time

from markitdown import MarkItDown
import win32com.client as win32

import pythoncom

pythoncom.CoInitialize()
xl=win32.Dispatch("Word.Application",pythoncom.CoInitialize())

def _convert_document(input_path, output_path, format_code):
    """
    使用 Microsoft Word 將單一文件轉換為指定格式。

    :param input_path: 來源檔案的絕對路徑。
    :param output_path: 輸出檔案的絕對路徑。
    :param format_code: Word 的 WdSaveFormat 枚舉值。
    """
    # 確保路徑是絕對路徑，COM 操作需要這個
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    # 啟動 Word 應用程式並設定為不可見
    word = win32.Dispatch('Word.Application')
    word.Visible = False

    doc = word.Documents.Open(input_path)

    
    # 另存為指定格式
    doc.SaveAs2(output_path, FileFormat=format_code)

    doc.Close(0) # 0 代表不儲存變更後關閉
    word.Quit()
            
_WD_FORMAT = {
	'docx': 16,
	'pdf': 17,
	'odt': 23,
	'doc': 0,
	'txt': 7,
	'rtf': 6
}

class MicrosoftException(Exception):
	pass

_md_converter = MarkItDown()
def convert(filename: str, is_show: bool = True) -> str:
	new_filename = None
	if filename.split(".")[-1] not in ("docx", "pptx"):
		base, ext = os.path.splitext(filename)
		new_filename = base + ".docx"
		for _ in range(3):
			try:
				_convert_document(filename, new_filename, _WD_FORMAT['docx'])
				break
			except Exception as e:
				err = e
				if is_show:
					print(f"嘗試轉換 {filename} 為 {new_filename} 失敗，3秒後重試: {e}")
				time.sleep(3)
				continue
		else:
			raise MicrosoftException() from err
		filename = new_filename

    # 使用 MarkItDown 將 Word 文件轉換為 Markdown
	markdown = _md_converter.convert(filename)
	if new_filename is not None:
		os.remove(new_filename)
	return markdown.text_content

if __name__ == "__main__":
	filename = "temp/7584_3.doc"
	text = convert(filename)
	with open("temp/7584_3.md", "w", encoding="utf-8") as f:
		f.write(text)