package main

import (
	"bufio"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const (
	DefaultDataFileName = "pcrypt.dta"
	SeedSize            = 16
	NonceSize           = 12
)

type Store struct {
	Apps map[string]map[string]string `json:"apps"`
	seed []byte                       `json:"-"`
}

func main() {
	rawArgs := os.Args[1:]
	dataFile, args := extractDataFileFlag(rawArgs)

	if len(args) < 1 || args[0] == "--help" || args[0] == "-h" || args[0] == "help" {
		printUsage()
		os.Exit(0)
	}

	cmd := args[0]
	cmdArgs := args[1:]

	switch cmd {
	case "set":
		handleSet(cmdArgs, dataFile)
	case "unset":
		handleUnset(cmdArgs, dataFile)
	case "load":
		handleLoad(cmdArgs, dataFile)
	case "unload":
		handleUnload(cmdArgs, dataFile)
	case "show":
		handleShow(cmdArgs, dataFile)
	case "list":
		handleList(dataFile)
	case "init-shell":
		handleInitShell()
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n\n", cmd)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("pcrypt - Encrypted environment variable manager")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  pcrypt [flags] <command> [arguments]")
	fmt.Println()
	fmt.Println("Flags:")
	fmt.Println("  --data-file, -d <path>    Specify custom path to pcrypt.dta file")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  set <app> <KEY=VALUE...>  Save one or more key-value pairs under <app>")
	fmt.Println("  unset <app> [KEY...]      Remove a key (or whole app set) from pcrypt.dta")
	fmt.Println("  load <app>                Output shell commands to export env variables")
	fmt.Println("  load <app> --file <path>  Write/merge env variables directly into a .env file")
	fmt.Println("  unload <app>              Output shell commands to unset env variables")
	fmt.Println("  show <app>                Display current shell environment status for <app> keys")
	fmt.Println("  list                      Display all saved apps and unencrypted key-value pairs")
	fmt.Println("  init-shell                Print bash wrapper function for shell evaluation")
	fmt.Println("  --help, -h                Show this help text")
}

func extractDataFileFlag(args []string) (string, []string) {
	var dataFile string
	var filtered []string

	for i := 0; i < len(args); i++ {
		if (args[i] == "--data-file" || args[i] == "-d") && i+1 < len(args) {
			dataFile = args[i+1]
			i++
		} else if strings.HasPrefix(args[i], "--data-file=") {
			dataFile = strings.TrimPrefix(args[i], "--data-file=")
		} else if strings.HasPrefix(args[i], "-d=") {
			dataFile = strings.TrimPrefix(args[i], "-d=")
		} else {
			filtered = append(filtered, args[i])
		}
	}
	return dataFile, filtered
}

func deriveKey(seed []byte) ([]byte, error) {
	hostname, err := os.Hostname()
	if err != nil {
		return nil, fmt.Errorf("failed to retrieve hostname: %w", err)
	}

	h := sha256.New()
	h.Write(seed)
	h.Write([]byte(strings.ToLower(strings.TrimSpace(hostname))))
	return h.Sum(nil), nil
}

func getDataFilePath(customPath string) (string, error) {
	if customPath != "" {
		return filepath.Abs(customPath)
	}
	if envPath := os.Getenv("PCRYPT_DATA_FILE"); envPath != "" {
		return filepath.Abs(envPath)
	}
	execPath, err := os.Executable()
	if err != nil {
		return "", err
	}
	realPath, err := filepath.EvalSymlinks(execPath)
	if err != nil {
		return "", err
	}
	return filepath.Join(filepath.Dir(realPath), DefaultDataFileName), nil
}

func loadStore(customPath string) (*Store, error) {
	path, err := getDataFilePath(customPath)
	if err != nil {
		return nil, err
	}

	if _, err := os.Stat(path); os.IsNotExist(err) {
		seed := make([]byte, SeedSize)
		if _, err := io.ReadFull(rand.Reader, seed); err != nil {
			return nil, fmt.Errorf("failed to generate random seed: %w", err)
		}
		return &Store{
			Apps: make(map[string]map[string]string),
			seed: seed,
		}, nil
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	minHeaderSize := SeedSize + NonceSize
	if len(data) < minHeaderSize {
		return nil, errors.New("corrupted data file: header too short")
	}

	seed := data[:SeedSize]
	nonce := data[SeedSize:minHeaderSize]
	ciphertext := data[minHeaderSize:]

	key, err := deriveKey(seed)
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, fmt.Errorf("decryption failed: %w", err)
	}

	var store Store
	if err := json.Unmarshal(plaintext, &store); err != nil {
		return nil, err
	}
	if store.Apps == nil {
		store.Apps = make(map[string]map[string]string)
	}
	store.seed = seed
	return &store, nil
}

func saveStore(store *Store, customPath string) error {
	path, err := getDataFilePath(customPath)
	if err != nil {
		return err
	}

	if len(store.seed) == 0 {
		store.seed = make([]byte, SeedSize)
		if _, err := io.ReadFull(rand.Reader, store.seed); err != nil {
			return fmt.Errorf("failed generating seed: %w", err)
		}
	}

	key, err := deriveKey(store.seed)
	if err != nil {
		return err
	}

	plaintext, err := json.Marshal(store)
	if err != nil {
		return err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return err
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return err
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return err
	}

	ciphertext := gcm.Seal(nil, nonce, plaintext, nil)

	payload := make([]byte, 0, len(store.seed)+len(nonce)+len(ciphertext))
	payload = append(payload, store.seed...)
	payload = append(payload, nonce...)
	payload = append(payload, ciphertext...)

	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, payload, 0600)
}

func handleSet(args []string, customPath string) {
	if len(args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: pcrypt [--data-file <path>] set <app> <KEY=VALUE...>\n")
		os.Exit(1)
	}

	appName := args[0]
	keyValPairs := args[1:]

	store, err := loadStore(customPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading store: %v\n", err)
		os.Exit(1)
	}

	if _, exists := store.Apps[appName]; !exists {
		store.Apps[appName] = make(map[string]string)
	}

	for _, pair := range keyValPairs {
		parts := strings.SplitN(pair, "=", 2)
		if len(parts) != 2 {
			fmt.Fprintf(os.Stderr, "Invalid key-value pair '%s'. Expected KEY=VALUE\n", pair)
			os.Exit(1)
		}
		store.Apps[appName][parts[0]] = parts[1]
	}

	if err := saveStore(store, customPath); err != nil {
		fmt.Fprintf(os.Stderr, "Error saving store: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Updated environment variables for '%s'.\n", appName)
}

func handleUnset(args []string, customPath string) {
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Usage: pcrypt [--data-file <path>] unset <app> [KEY...]\n")
		os.Exit(1)
	}

	appName := args[0]
	keysToRemove := args[1:]

	store, err := loadStore(customPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading store: %v\n", err)
		os.Exit(1)
	}

	appVars, exists := store.Apps[appName]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: app set '%s' not found.\n", appName)
		os.Exit(1)
	}

	if len(keysToRemove) == 0 {
		delete(store.Apps, appName)
		fmt.Printf("Removed environment set '%s'.\n", appName)
	} else {
		for _, k := range keysToRemove {
			if _, found := appVars[k]; found {
				delete(appVars, k)
				fmt.Printf("Unset variable '%s' from '%s'.\n", k, appName)
			} else {
				fmt.Fprintf(os.Stderr, "Warning: key '%s' not found in '%s'.\n", k, appName)
			}
		}
		if len(appVars) == 0 {
			delete(store.Apps, appName)
		}
	}

	if err := saveStore(store, customPath); err != nil {
		fmt.Fprintf(os.Stderr, "Error saving store: %v\n", err)
		os.Exit(1)
	}
}

func handleLoad(args []string, customPath string) {
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Usage: pcrypt [--data-file <path>] load <app> [--file <path>]\n")
		os.Exit(1)
	}

	appName := args[0]
	filePath := ""

	for i := 1; i < len(args); i++ {
		if args[i] == "--file" && i+1 < len(args) {
			filePath = args[i+1]
			i++
		}
	}

	store, err := loadStore(customPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading store: %v\n", err)
		os.Exit(1)
	}

	envVars, exists := store.Apps[appName]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: app set '%s' not found\n", appName)
		os.Exit(1)
	}

	if filePath != "" {
		if err := writeToEnvFile(filePath, envVars); err != nil {
			fmt.Fprintf(os.Stderr, "Error updating file %s: %v\n", filePath, err)
			os.Exit(1)
		}
		return
	}

	for k, v := range envVars {
		fmt.Printf("export %s='%s';\n", k, strings.ReplaceAll(v, "'", "'\\''"))
	}
}

func handleUnload(args []string, customPath string) {
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Usage: pcrypt [--data-file <path>] unload <app>\n")
		os.Exit(1)
	}

	appName := args[0]

	store, err := loadStore(customPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading store: %v\n", err)
		os.Exit(1)
	}

	envVars, exists := store.Apps[appName]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: app set '%s' not found\n", appName)
		os.Exit(1)
	}

	for k := range envVars {
		fmt.Printf("unset %s;\n", k)
	}
}

func handleShow(args []string, customPath string) {
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Usage: pcrypt [--data-file <path>] show <app>\n")
		os.Exit(1)
	}

	appName := args[0]
	store, err := loadStore(customPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading store: %v\n", err)
		os.Exit(1)
	}

	envVars, exists := store.Apps[appName]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: app set '%s' not found\n", appName)
		os.Exit(1)
	}

	keys := make([]string, 0, len(envVars))
	for k := range envVars {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		if val, set := os.LookupEnv(k); set {
			fmt.Printf("%s = %s\n", k, val)
		} else {
			fmt.Printf("%s = <not set>\n", k)
		}
	}
}

func handleList(customPath string) {
	store, err := loadStore(customPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading store: %v\n", err)
		os.Exit(1)
	}

	if len(store.Apps) == 0 {
		fmt.Println("No environment variable sets stored in data file.")
		return
	}

	apps := make([]string, 0, len(store.Apps))
	for app := range store.Apps {
		apps = append(apps, app)
	}
	sort.Strings(apps)

	for _, app := range apps {
		vars := store.Apps[app]
		fmt.Printf("[%s]\n", app)
		if len(vars) == 0 {
			fmt.Println("  (no variables)")
			continue
		}
		keys := make([]string, 0, len(vars))
		for k := range vars {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			fmt.Printf("  %s = %s\n", k, vars[k])
		}
		fmt.Println()
	}
}

func handleInitShell() {
	fmt.Println(`pcrypt() {
    local _pcrypt
    if command -v pcrypt >/dev/null 2>&1; then
        _pcrypt="$(command -v pcrypt)"
    else
        _pcrypt="./pcrypt"
    fi
    if { [ "$1" = "load" ] || [ "$1" = "unload" ]; } && [[ " $* " != *" --file "* ]]; then
        eval "$("$_pcrypt" "$@")"
    else
        "$_pcrypt" "$@"
    fi
}`)
}

func writeToEnvFile(filePath string, newVars map[string]string) error {
	var existingLines []string
	existingKeys := make(map[string]bool)

	if _, err := os.Stat(filePath); err == nil {
		file, err := os.Open(filePath)
		if err != nil {
			return err
		}
		scanner := bufio.NewScanner(file)
		for scanner.Scan() {
			line := scanner.Text()
			trimmed := strings.TrimSpace(line)
			if trimmed != "" && !strings.HasPrefix(trimmed, "#") && strings.Contains(trimmed, "=") {
				key := strings.SplitN(trimmed, "=", 2)[0]
				existingKeys[key] = true
			}
			existingLines = append(existingLines, line)
		}
		file.Close()
	}

	scanner := bufio.NewScanner(os.Stdin)
	updatedVars := make(map[string]string)

	for k, v := range newVars {
		if existingKeys[k] {
			fmt.Fprintf(os.Stderr, "Variable '%s' already exists in %s. Overwrite? [y/N]: ", k, filePath)
			scanner.Scan()
			ans := strings.ToLower(strings.TrimSpace(scanner.Text()))
			if ans == "y" || ans == "yes" {
				updatedVars[k] = v
			}
		} else {
			updatedVars[k] = v
		}
	}

	var outputLines []string
	overwritten := make(map[string]bool)

	for _, line := range existingLines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && !strings.HasPrefix(trimmed, "#") && strings.Contains(trimmed, "=") {
			key := strings.SplitN(trimmed, "=", 2)[0]
			if val, replace := updatedVars[key]; replace {
				outputLines = append(outputLines, fmt.Sprintf("%s=%s", key, val))
				overwritten[key] = true
				continue
			}
		}
		outputLines = append(outputLines, line)
	}

	for k, v := range updatedVars {
		if !overwritten[k] {
			outputLines = append(outputLines, fmt.Sprintf("%s=%s", k, v))
		}
	}

	return os.WriteFile(filePath, []byte(strings.Join(outputLines, "\n")+"\n"), 0644)
}
