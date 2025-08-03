import { Container, Image, Input, Text } from "@chakra-ui/react"
import {
  Link as RouterLink,
  createFileRoute,
  redirect,
} from "@tanstack/react-router"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FiLock, FiMail } from "react-icons/fi"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"
import { InputGroup } from "@/components/ui/input-group"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import Logo from "/assets/images/fastapi-logo.svg"
import { emailPattern, passwordRules } from "../utils"

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
})

function Login() {

  // 인증 관련 모든 기능을 관리하는 커스텀 훅
  // 로그인, 회원가입, 로그아웃, 사용자 정보 관리
  const { loginMutation, error, resetError } = useAuth()
  //
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AccessToken>({
    mode: "onBlur",
    criteriaMode: "all", // 모든 에러를 수집 | firstError 기본값 - 첫번째 에러만
    defaultValues: {
      username: "",
      password: "",
    },
  }) // 폼의 모든 상태와 기능을 한 곳에서 관리
  // mode 의 옵션
  // 5가지 옵션:
  // "onSubmit"  // 기본값 - 제출할 때만 검증
  // "onBlur"    // ⭐ 현재 설정 - 포커스 벗어날 때 검증
  // "onChange"  // 타이핑할 때마다 검증
  // "onTouched" // 한 번 터치된 후 onChange마다 검증
  // "all"       // 모든 이벤트에서 검증

  // register가 반환하는 객체
  // {
  // name: "username",           // 필드명
  // onChange: (event) => {},    // 변경 핸들러
  // onBlur: (event) => {},      // 블러 핸들러
  // ref: (element) => {}        // DOM 참조
  // }



  const onSubmit: SubmitHandler<AccessToken> = async (data) => {
    if (isSubmitting) return

    resetError()

    try {
      // mutateAsync: TanStack Query의 useMutation 에서 제공하는 Promise 기반 실행 함수
      await loginMutation.mutateAsync(data)
    } catch {
      // error is handled by useAuth hook
    }
  }

  return (
    <>
      <Container
        as="form" // 실제 DOM 에는 <form> 태그가 적용
        onSubmit={handleSubmit(onSubmit)} // 폼 제출 이벤트 핸들러
        h="100vh"
        maxW="sm"
        alignItems="stretch"
        justifyContent="center"
        gap={4}
        centerContent
      >
        <Image
          src={Logo}
          alt="FastAPI logo"
          height="auto"
          maxW="2xs"
          alignSelf="center"
          mb={4}
        />
        <Field
          invalid={!!errors.username} // 필드가 유효하지 않을때 (지금 이 필드가 에러 상태야!)
          errorText={errors.username?.message || !!error} // 표시할 에러 메시지
        >
          {/* Input 컴포넌트를 하나로 묶어 통합된 입력 컴포넌트처럼 보이게 함 */}
          <InputGroup w="100%" startElement={<FiMail />}>
            <Input
              id="username"
              {...register("username", {
                required: "Username is required",
                pattern: emailPattern,
              })}
              placeholder="Email"
              type="email"
            />
          </InputGroup>
        </Field>
        <PasswordInput
          type="password"
          startElement={<FiLock />}
          {...register("password", passwordRules())}
          placeholder="Password"
          errors={errors}
        />
        <RouterLink to="/recover-password" className="main-link">
          Forgot Password?
        </RouterLink>
        {/* 아래 버튼이 폼 제출 트리거 */}
        <Button variant="solid" type="submit" loading={isSubmitting} size="md">
          Log In
        </Button>
        <Text>
          Don't have an account?{" "}
          <RouterLink to="/signup" className="main-link">
            Sign Up
          </RouterLink>
        </Text>
      </Container>
    </>
  )
}
