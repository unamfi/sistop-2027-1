CC = gcc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic

all: gatos_ratones.exe

gatos_ratones.exe: gatos_ratones.c
	$(CC) $(CFLAGS) gatos_ratones.c -o gatos_ratones.exe

run: gatos_ratones.exe
	./gatos_ratones.exe

clean:
	rm -f gatos_ratones.exe gatos_ratones
