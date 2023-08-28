package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"strings"
)

func main() {
	// Получаем GitLab Private Token из переменной окружения
	gitlabPrivateToken := os.Getenv("GITLAB_PRIVATE_TOKEN")
	if gitlabPrivateToken == "" {
		fmt.Println("GITLAB_PRIVATE_TOKEN не установлен")
		fmt.Println("Пожалуйста, установите GitLab Private Token в качестве GITLAB_PRIVATE_TOKEN")
		os.Exit(1)
	}

	// Получаем необходимые переменные окружения
	ciProjectURL := os.Getenv("CI_PROJECT_URL")
	ciProjectID := os.Getenv("CI_PROJECT_ID")
	ciCommitRefName := os.Getenv("CI_COMMIT_REF_NAME")
	gitlabUserID := os.Getenv("GITLAB_USER_ID")

	// Проверяем наличие всех необходимых переменных окружения
	if ciProjectURL == "" || ciProjectID == "" || ciCommitRefName == "" || gitlabUserID == "" {
		fmt.Println("Одна или несколько переменных окружения не установлены.")
		os.Exit(1)
	}

	// Разбиваем URL проекта, чтобы получить базовый URL для API
	hostParts := strings.SplitN(ciProjectURL, "/", 4)
	if len(hostParts) < 3 {
		fmt.Println("Неверный формат CI_PROJECT_URL")
		os.Exit(1)
	}

	// Формируем URL для доступа к API GitLab
	gitlabAPIURL := fmt.Sprintf("%s/api/v4/projects/%s", hostParts[0]+"//"+hostParts[2], ciProjectID)

	// Создаем HTTP клиент с добавлением токена в заголовки запросов
	client := &http.Client{}
	req, err := http.NewRequest("GET", gitlabAPIURL, nil)
	if err != nil {
		fmt.Println("Ошибка создания запроса:", err)
		os.Exit(1)
	}
	req.Header.Add("Private-Token", gitlabPrivateToken)

	// Получаем информацию о проекте через API
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Ошибка получения информации о проекте:", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	// Декодируем информацию о проекте из JSON
	var projectInfo map[string]interface{}
	err = json.NewDecoder(resp.Body).Decode(&projectInfo)
	if err != nil {
		fmt.Println("Ошибка декодирования информации о проекте:", err)
		os.Exit(1)
	}

	// Определяем целевую ветку для слияния
	targetBranch := projectInfo["default_branch"].(string)

	// Формируем тело запроса на создание MR
	requestBody := map[string]interface{}{
		"id":                   ciProjectID,
		"source_branch":        ciCommitRefName,
		"target_branch":        targetBranch,
		"remove_source_branch": false, // Пока мы не используем каждый свою ветку, то не будем удалять develop
		"title":                "WIP: " + ciCommitRefName,
		"assignee_id":          gitlabUserID,
	}

	// Кодируем тело запроса в формат JSON
	requestBodyBytes, err := json.Marshal(requestBody)
	if err != nil {
		fmt.Println("Ошибка кодирования тела запроса:", err)
		os.Exit(1)
	}

	// Создаем HTTP клиент для POST запроса на создание MR
	createMRClient := &http.Client{}
	createMRReq, err := http.NewRequest("POST", gitlabAPIURL+"/merge_requests", bytes.NewBuffer(requestBodyBytes))
	if err != nil {
		fmt.Println("Ошибка создания запроса на создание MR:", err)
		os.Exit(1)
	}
	createMRReq.Header.Add("Private-Token", gitlabPrivateToken)
	createMRReq.Header.Add("Content-Type", "application/json")

	// Отправляем запрос на создание MR
	createMRResp, err := createMRClient.Do(createMRReq)
	if err != nil {
		fmt.Println("Ошибка создания MR:", err)
		os.Exit(1)
	}
	defer createMRResp.Body.Close()

	fmt.Println("Статус код ответа при создании MR:", createMRResp.StatusCode)

	if createMRResp.StatusCode == http.StatusCreated {
		fmt.Printf("Открыт новый запрос на слияние: WIP: %s, и назначен вам\n", ciCommitRefName)
	} else {
		fmt.Println("Ошибка создания MR")
		// Вывести содержимое ответа API для отладки
		responseBytes, _ := ioutil.ReadAll(createMRResp.Body)
		fmt.Println("Ответ API:", string(responseBytes))
	}
}
