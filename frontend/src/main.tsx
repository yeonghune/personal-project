import {
  MutationCache, // POST/PUT/DELETE 등 데이터 변경 요청을 캐싱
  QueryCache, // GET 요청 결과를 캐싱
  QueryClient, // 전체 쿼리 시스템의 중앙 관리자
  QueryClientProvider, // 하위 컴포넌트들이 QueryClient에 접근할 수 있게 해줌
} from "@tanstack/react-query" // 서버 상태 관리를 위한 라이브러리
import { RouterProvider, createRouter } from "@tanstack/react-router"
// 안전한 클라이언트 사이드 라우팅 라이브러리
// createRouter: 라우터 인스턴스 생성
// RouterProvider: 라우터를 React 앱에 제공하는 Context Provider
import React, { StrictMode } from "react" // 리액트의 기본 객체, 개발모드에서 추가 검사 진행
import ReactDOM from "react-dom/client" // 리액트를 DOM에 렌더링하기 위한 라이브러리
import { routeTree } from "./routeTree.gen" // 자동 생성된 라우트 트리 파일

import { ApiError, OpenAPI } from "./client" // 자동 생성된 API 클라이언트 모듈
import { CustomProvider } from "./components/ui/provider" // 커스텀 UI 컴포넌트

// API 설정
OpenAPI.BASE = import.meta.env.VITE_API_URL // API 기본 URL 설정: 환경변수에서 API 서버 주소 가져옴
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
} // localStorage 액세스 토큰을 자동으로 가져와 API 요청 (HTTP 헤더)에 포함

// 인증 에러 처리
const handleApiError = (error: Error) => {
  if (error instanceof ApiError && [401, 403].includes(error.status)) {
    localStorage.removeItem("access_token") // localStorage에 있는 잘못된 access_token 제거
    window.location.href = "/login" // 로그인 페이지로 리다이렉트
  }
}

// 모든 캐시에 에러 핸들러 작용
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

// routeTree에서 정의된 라우트 구조 사용
const router = createRouter({ routeTree })
// TypeScript 타입 안정성을 위한 모듈 선언 확장
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

// 애플리케이션 렌더링
ReactDOM.createRoot(document.getElementById("root")!).render(
  // 리액트의 개발 모드 검사 활성화
  <StrictMode>
    {/* 커스텀 UI 테마/설정 제공*/}
    <CustomProvider>
      {/* React Query 클라이언트를 전역으로 제공 */}
      <QueryClientProvider client={queryClient}>
        {/* 라우터 기능 제공 */}
        <RouterProvider router={router} />
      </QueryClientProvider>
    </CustomProvider>
  </StrictMode>,
)
