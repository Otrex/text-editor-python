from bisect import bisect_right

from editor.domain.position import Position


class TextModelE:
	def __init__(self, text=""):
		self._text = text
		self._rebuild_line_starts()

	def _rebuild_line_starts(self):
		self._line_starts = [0]
		self._line_starts.extend(index + 1 for index, character in enumerate(self._text) if character == "\n")

	def get_text(self):
		return self._text

	@property
	def line_count(self):
		return len(self._line_starts)

	def get_line_content(self, line):
		if not 0 <= line < self.line_count:
			raise IndexError("line index out of range")
		start = self._line_starts[line]
		end = self._text.find("\n", start)
		return self._text[start : len(self._text) if end == -1 else end]

	def offset_at(self, position):
		line = min(max(position.line, 0), self.line_count - 1)
		start = self._line_starts[line]
		end = self._text.find("\n", start)
		line_length = (len(self._text) if end == -1 else end) - start
		column = min(max(position.column, 0), line_length)
		return start + column

	def position_at(self, offset):
		offset = min(max(offset, 0), len(self._text))
		line = bisect_right(self._line_starts, offset) - 1
		column = offset - self._line_starts[line]
		return Position(line, column)

	def insert(self, offset, value):
		self.replace(offset, offset, value)

	def delete(self, start, end):
		self.replace(start, end, "")

	def replace(self, start, end, value):
		start = min(max(start, 0), len(self._text))
		end = min(max(end, start), len(self._text))
		self._text = self._text[:start] + value + self._text[end:]
		self._rebuild_line_starts()




class TextModel:
    def __init__(self, text=""):
        self._buffer = list(text)
        self._gap_start = len(self._buffer)
        self._gap_end = len(self._buffer)

        self._rebuild_line_starts()

    @property
    def _gap_size(self):
        return self._gap_end - self._gap_start

    def _ensure_gap(self, size):
        """Ensure that the gap contains at least `size` characters."""
        if self._gap_size >= size:
            return

        additional = max(size - self._gap_size, 64)

        self._buffer[self._gap_end:self._gap_end] = [None] * additional
        self._gap_end += additional

    def _move_gap(self, offset):
        """Move the gap so that it starts at `offset`."""
        offset = min(max(offset, 0), self._length())

        if offset == self._gap_start:
            return

        if offset < self._gap_start:
            # Move text before the gap to the right.
            count = self._gap_start - offset

            for i in range(count - 1, -1, -1):
                self._buffer[self._gap_end - count + i] = (
                    self._buffer[offset + i]
                )

            self._gap_start -= count
            self._gap_end -= count

        else:
            # Move text after the gap to the left.
            count = offset - self._gap_start

            for i in range(count):
                self._buffer[self._gap_start + i] = (
                    self._buffer[self._gap_end + i]
                )

            self._gap_start += count
            self._gap_end += count

    def _length(self):
        return len(self._buffer) - self._gap_size

    def _char_at(self, offset):
        """Return the character at logical offset."""
        if offset < self._gap_start:
            return self._buffer[offset]

        return self._buffer[offset + self._gap_size]

    def _text_slice(self, start, end):
        """Return logical text in [start:end]."""
        if start >= end:
            return ""

        gap_start = self._gap_start
        gap_end = self._gap_end
        gap_size = self._gap_size

        if end <= gap_start:
            return "".join(self._buffer[start:end])

        if start >= gap_start:
            return "".join(
                self._buffer[start + gap_size:end + gap_size]
            )

        # Slice crosses the gap.
        left = "".join(self._buffer[start:gap_start])
        right = "".join(self._buffer[gap_end:gap_end + (end - gap_start)])

        return left + right

    def _rebuild_line_starts(self):
        self._line_starts = [0]

        length = self._length()

        for index in range(length):
            if self._char_at(index) == "\n":
                self._line_starts.append(index + 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_text(self):
        return self._text_slice(0, self._length())

    @property
    def line_count(self):
        return len(self._line_starts)

    def get_line_content(self, line):
        if not 0 <= line < self.line_count:
            raise IndexError("line index out of range")

        start = self._line_starts[line]

        if line + 1 < self.line_count:
            end = self._line_starts[line + 1] - 1
        else:
            end = self._length()

        return self._text_slice(start, end)

    def offset_at(self, position):
        line = min(
            max(position.line, 0),
            self.line_count - 1,
        )

        start = self._line_starts[line]

        if line + 1 < self.line_count:
            end = self._line_starts[line + 1] - 1
        else:
            end = self._length()

        line_length = end - start

        column = min(
            max(position.column, 0),
            line_length,
        )

        return start + column

    def position_at(self, offset):
        offset = min(
            max(offset, 0),
            self._length(),
        )

        line = bisect_right(self._line_starts, offset) - 1
        column = offset - self._line_starts[line]

        return Position(line, column)

    def insert(self, offset, value):
        self.replace(offset, offset, value)

    def delete(self, start, end):
        self.replace(start, end, "")

    def replace(self, start, end, value):
        length = self._length()

        start = min(max(start, 0), length)
        end = min(max(end, start), length)

        # Move the gap to the beginning of the replacement.
        self._move_gap(start)

        # Delete existing text by expanding the gap.
        deleted_length = end - start
        self._gap_end += deleted_length

        # Make room for the inserted text.
        self._ensure_gap(len(value))

        # Insert into the gap.
        for character in value:
            self._buffer[self._gap_start] = character
            self._gap_start += 1

        self._rebuild_line_starts()