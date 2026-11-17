CXX = g++

CXXFLAGS = -Wall -Wextra -std=c++17 -Iinclude

SRC = src/main.cpp \
      src/FiUnamFS.cpp \
      src/Utils.cpp

TARGET = fiunamfs

all:
	$(CXX) $(SRC) $(CXXFLAGS) -o $(TARGET)

clean:
	rm -f $(TARGET)