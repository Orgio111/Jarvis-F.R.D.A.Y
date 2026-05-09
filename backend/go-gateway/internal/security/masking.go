package security

import "regexp"

var secretPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)(api[_-]?key|api[_-]?secret|auth[_-]?token|bearer\s+)\S+`),
	regexp.MustCompile(`(?i)(nvidia|openrouter|openai)[_-]?key[=:]\s*\S+`),
	regexp.MustCompile(`(?i)password[=:]\s*\S+`),
	regexp.MustCompile(`(?i)secret[=:]\s*\S+`),
}

// MaskSecrets replaces known secret patterns in a string with [REDACTED].
func MaskSecrets(s string) string {
	for _, re := range secretPatterns {
		s = re.ReplaceAllStringFunc(s, func(match string) string {
			// Keep key name, replace value
			idx := re.FindStringIndex(match)
			if idx == nil {
				return "[REDACTED]"
			}
			return "[REDACTED]"
		})
	}
	return s
}

// MaskHeader returns a masked version of a header value for logging.
func MaskHeader(name, value string) string {
	switch name {
	case "Authorization", "X-Api-Key", "X-Auth-Token":
		if len(value) <= 8 {
			return "[REDACTED]"
		}
		return value[:4] + "..." + "[REDACTED]"
	}
	return value
}
