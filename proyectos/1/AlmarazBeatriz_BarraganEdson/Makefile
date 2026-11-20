CXX = g++

CXXFLAGS = -Wall -Wextra -std=c++17 -Iinclude

SRC = src/main.cpp \
      src/FiUnamFS.cpp \
      src/DirectoryOperations.cpp \
      src/FileOperations.cpp \
      src/Utils.cpp

ifeq ($(OS),Windows_NT)
TARGET = fiunamfs.exe
TEST_TARGET = prueba_concurrencia.exe
else
TARGET = fiunamfs
TEST_TARGET = prueba_concurrencia
endif

TEST_SRC = tests/test_listing.cpp \
           src/FiUnamFS.cpp \
           src/DirectoryOperations.cpp \
           src/FileOperations.cpp \
           src/Utils.cpp

all:
	$(CXX) $(SRC) $(CXXFLAGS) -o $(TARGET)

test:
	$(CXX) $(TEST_SRC) $(CXXFLAGS) -pthread -o $(TEST_TARGET)

clean:
ifeq ($(OS),Windows_NT)
	cmd /C "del /Q fiunamfs fiunamfs.exe prueba_concurrencia prueba_concurrencia.exe 2>NUL"
else
	rm -f $(TARGET) $(TARGET).exe prueba_concurrencia prueba_concurrencia.exe
endif