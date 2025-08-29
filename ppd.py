import os
import shutil

import pypandoc

def convert(input_path: str):
	if input_path.find(".") == -1:
		shutil.copy(input_path, input_path + ".odt")
		input_path = input_path + ".odt"
	print(f"convert {input_path}")
	output_path = os.path.splitext(input_path)[0] + ".docx"
	pypandoc.convert_file(input_path, "docx", outputfile=output_path)
	output_path = os.path.splitext(input_path)[0] + ".md"
	pypandoc.convert_file(input_path, "md", outputfile=output_path)
	return output_path

if __name__ == "__main__":
	convert("temp/7683_2None")
	convert("temp/7673_2None")
	convert("temp/7669_2.doc")
	convert("temp/7640_1.doc")