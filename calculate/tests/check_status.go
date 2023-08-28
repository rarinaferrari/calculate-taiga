package main

import (
	"context"
	"fmt"
	"os"
	"time"
	"strings"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/client"
)

func main() {
	cli, err := client.NewEnvClient()
	if err != nil {
		panic(err)
	}

	maxRetries := 5
	retryInterval := time.Second

	for i := 1; i <= maxRetries; i++ {
		fmt.Printf("Попытка %d:\n", i)

		containers, err := cli.ContainerList(context.Background(), types.ContainerListOptions{All: true})
		if err != nil {
			panic(err)
		}

		allContainersUp := true

		for _, container := range containers {
			fmt.Printf("Имя контейнера: %s\n", container.Names[0])
			fmt.Printf("ID контейнера: %s\n", container.ID)
			fmt.Printf("Статус контейнера: %s\n", container.Status)
			fmt.Println("-------------------------")

			if strings.Contains(container.Names[0], "runner") {
				continue
			}

			if container.State != "running" {
				allContainersUp = false
			}
		}

		if allContainersUp {
			fmt.Println("Все контейнеры в состоянии Up")
			break
		} else if i < maxRetries {
			fmt.Printf("Некоторые контейнеры не в состоянии Up. Ожидание %d секунд...\n", retryInterval/time.Second)
			time.Sleep(retryInterval)
		} else {
			fmt.Println("Некоторые контейнеры не в состоянии Up на последней попытке")
			os.Exit(1)
		}
	}
}
