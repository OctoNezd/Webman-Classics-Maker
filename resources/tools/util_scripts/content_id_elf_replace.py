import os
import json
from global_paths import App as AppPaths

class Elf_replace:
	def execute(self):
		with open(os.path.join(AppPaths.game_work_dir, 'pkg.json')) as f:
			json_data = json.load(f)

		# load it
		with open(os.path.join(AppPaths.util_resources, 'EBOOT.ELF.BAK'), 'rb') as f:
			file = f.read()
			
			try:
				file = file.replace('PKGLAUNCH', str(json_data['title_id']))

				newFile = open(os.path.join(AppPaths.scetool, 'EBOOT.ELF'), 'wb')
				newFileByteArray = bytearray(file)
				newFile.write(newFileByteArray)

				print('[2/5] Execution of \'content_id_elf_replace.py\':  DONE')
				print('-----------------------------------------------------')
				return True
			except Exception as e:
				print('[2/5] Execution of \'content_id_elf_replace.py\':  FAILED')
				print(e.message)
				print('-----------------------------------------------------')
				return False