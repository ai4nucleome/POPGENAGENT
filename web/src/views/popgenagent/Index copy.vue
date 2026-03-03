<template>
    <div class="bg-gray-100 flex items-center justify-center h-screen bg-cover bg-center background">
        <div class="flex">
            <div class="shrink-0 p-10 text-white w-[560px]">
                <div class="flex flex-col h-full">
                    <h1 class="text-5xl h-16 font-bold mb-4 bg-gradient-to-r from-blue-500 via-purple-500 to-[#6943fa] gradient-text">PopGenAgent</h1>
                    <p class="text-xl text-black mt-4">An LLM-driven agent for single-cell dataanalysis, ensuring high-quality results withminimal effort.</p>
                </div>
            </div>
            <div class="shrink-0 p-10 rounded-lg bg-gray-100 max-w-2xl w-[400px] translate-x-4 shadow-lg">
                <h2 class="text-2xl font-bold mb-6">PopGenAgent</h2>
                <form class="space-y-5" @submit="onSubmit">
                    <div>
                        <label class="block text-sm font-medium text-gray-700" for="email">Email</label>
                        <input type="email" id="email"
                            class="w-full px-4 py-2 mt-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Enter your email">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700" for="password">Password</label>
                        <input type="password" id="password"
                            class="w-full px-4 py-2 mt-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Enter your password">
                    </div>
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <input type="checkbox" id="remember"
                                class="h-4 w-4 text-blue-500 border-gray-300 rounded focus:ring-blue-400">
                            <label for="remember" class="ml-2 text-sm text-gray-700">Remember me</label>
                        </div>
                        <RouterLink to="/register" class="text-sm text-blue-500 hover:underline">Register</RouterLink>
                    </div>
                    <button type="submit"
                        class="w-full px-4 py-2 bg-gradient-to-r from-blue-500 to-[#787ef4] text-white font-semibold rounded-lg shadow-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75">Sign In</button>
                </form>
            </div>
        </div>
        <Logo />
    </div>
</template>
<script setup lang="ts">
import Logo from '../../components/Logo.vue'
import useUserStore from "@/store/pageStore";
import * as cookie from "@/utils/cookie"

const userStore = useUserStore();

async function onSubmit(){
    cookie.setLogin("true");
    userStore.token = "true";
}
</script>
<style scoped lang="scss">
</style>