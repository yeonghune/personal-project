import type { FormEvent } from "react"
import { Box, Container, Flex, Heading, Input, Table, Textarea } from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { z } from "zod"

import { TodosService, type TodoPublic } from "../../client"
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "../../components/ui/pagination.tsx"
import { Button } from "../../components/ui/button"

const todosSearchSchema = z.object({
  page: z.number().catch(1),
})

const PER_PAGE = 5

function getTodosQueryOptions({ page }: { page: number }) {
  return {
    queryFn: () =>
      TodosService.readTodos({ skip: (page - 1) * PER_PAGE, limit: PER_PAGE }),
    queryKey: ["todos", { page }],
  }
}

export const Route = createFileRoute("/_layout/todos")({
  component: Todos,
  validateSearch: (search) => todosSearchSchema.parse(search),
})

function formatDate(dateString?: string | null) {
  if (!dateString) return "N/A"
  const d = new Date(dateString)
  if (Number.isNaN(d.getTime())) return "N/A"
  return d.toLocaleString()
}

function TodosTable() {
  const navigate = useNavigate({ from: Route.fullPath })
  const { page } = Route.useSearch()
  const queryClient = useQueryClient()

  const { data, isLoading, isPlaceholderData } = useQuery({
    ...getTodosQueryOptions({ page }),
    placeholderData: (prevData) => prevData,
  })

  const setPage = (page: number) =>
    navigate({
      search: (prev: { [key: string]: string }) => ({ ...prev, page }),
    })

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      TodosService.deleteTodo({ id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos"] })
    },
  })

  const todos = data?.data.slice(0, PER_PAGE) ?? []
  const count = data?.count ?? 0

  if (isLoading) {
    return <Box mt={6}>Loading...</Box>
  }

  if (todos.length === 0) {
    return <Box mt={6}>You don't have any todos yet</Box>
  }

  return (
    <>
      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader w="sm">ID</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Title</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Description</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Due</Table.ColumnHeader>
            <Table.ColumnHeader w="sm">Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {todos?.map((todo: TodoPublic) => (
            <Table.Row key={todo.id} opacity={isPlaceholderData ? 0.5 : 1}>
              <Table.Cell truncate maxW="sm">{todo.id}</Table.Cell>
              <Table.Cell truncate maxW="sm">{todo.title}</Table.Cell>
              <Table.Cell
                color={!todo.description ? "gray" : "inherit"}
                truncate
                maxW="30%"
              >
                {todo.description || "N/A"}
              </Table.Cell>
              <Table.Cell truncate maxW="sm">
                {formatDate(todo.due_time)}
              </Table.Cell>
              <Table.Cell>
              <Button
                  variant="ghost"
                  colorPalette="red"
                  size="xs"
                  loading={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(todo.id)}
                >
                  Delete
                </Button>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
      <Flex justifyContent="flex-end" mt={4}>
        <PaginationRoot
          count={count}
          pageSize={PER_PAGE}
          onPageChange={({ page }) => setPage(page)}
        >
          <Flex>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </Flex>
        </PaginationRoot>
      </Flex>
    </>
  )
}

function AddTodo() {
  const queryClient = useQueryClient()
  const { page } = Route.useSearch()
  const createMutation = useMutation({
    mutationFn: (data: { title: string; description?: string; due_time?: string }) =>
      TodosService.createTodo({ requestBody: data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["todos", { page }] })
    },
  })

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const formData = new FormData(form)
    const title = String(formData.get("title") || "").trim()
    const description = String(formData.get("description") || "").trim()
    const dueLocal = String(formData.get("due_time") || "").trim()

    if (!title) return

    const due_time = dueLocal ? new Date(dueLocal).toISOString() : undefined

    await createMutation.mutateAsync({ title, description: description || undefined, due_time })
    form.reset()
  }

  return (
    <Box mt={6} display="grid" gap={2}>
      <form onSubmit={handleSubmit}>
        <Box display="grid" gap={2}>
          <Input name="title" placeholder="Title" required />
          <Textarea name="description" placeholder="Description (optional)" />
          <Input name="due_time" type="datetime-local" placeholder="Due time (optional)" />
          <Button type="submit" loading={createMutation.isPending} alignSelf="start">
            Add Todo
          </Button>
        </Box>
      </form>
    </Box>
  )
}

function Todos() {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12}>
        Todos Management
      </Heading>
      <AddTodo />
      <TodosTable />
    </Container>
  )
}

export default Todos