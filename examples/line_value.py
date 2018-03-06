from trio_gpio import gpio

if __name__ == "__main__":
	with gpio.Chip(0) as c:
		with c.line(4) as l:
			print(l.value)
