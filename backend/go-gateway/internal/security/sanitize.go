package security

import (
	"html"
	"strings"
	"unicode/utf8"
)

const maxInputLength = 1_000_000 // 1 MB of text

// SanitizeString trims whitespace, escapes HTML entities, and enforces a max length.
func SanitizeString(s string) string {
	s = strings.TrimSpace(s)
	if len(s) > maxInputLength {
		// Truncate at valid UTF-8 boundary
		s = truncateUTF8(s, maxInputLength)
	}
	return html.EscapeString(s)
}

// SanitizeID validates that a string looks like a safe identifier (UUID / slug).
func SanitizeID(s string) string {
	var b strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') ||
			(r >= '0' && r <= '9') || r == '-' || r == '_' {
			b.WriteRune(r)
		}
	}
	return b.String()
}

func truncateUTF8(s string, maxBytes int) string {
	if len(s) <= maxBytes {
		return s
	}
	for i := maxBytes; i > 0; i-- {
		if utf8.RuneStart(s[i]) {
			return s[:i]
		}
	}
	return ""
}
