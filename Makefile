.PHONY: zip clean
zip:
	python3 tools/build_zip.py
clean:
	rm -f dist/mod_afei_expedition.zip
