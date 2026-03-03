<template>
    <div class="relative w-full h-screen overflow-hidden bg-dark-900">
        <!-- Dynamic background -->
        <div class="absolute inset-0 overflow-hidden">
            <!-- Gradient background layer -->
            <div class="absolute inset-0 bg-gradient-to-br from-dark-900 via-dark-800 to-dark-900"></div>
            
            <!-- Dynamic glow -->
            <div class="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-primary-500/20 blur-[120px] animate-pulse-slow"></div>
            <div class="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-accent-500/20 blur-[100px] animate-pulse-slow" style="animation-delay: 1s;"></div>
            <div class="absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-cyber-500/15 blur-[80px] animate-float"></div>
            
            <!-- Grid background -->
            <div class="absolute inset-0 opacity-[0.03]"
                style="background-image: linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 50px 50px;">
                </div>
            
            <!-- Floating particles -->
            <div v-for="i in 20" :key="i" 
                class="absolute w-1 h-1 bg-white/30 rounded-full animate-float"
                :style="{
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                    animationDelay: `${Math.random() * 5}s`,
                    animationDuration: `${5 + Math.random() * 5}s`
                }">
            </div>
        </div>

        <!-- Main content -->
        <div class="relative z-10 flex items-center justify-center h-full px-6">
            <div class="flex items-center gap-16 max-w-6xl mx-auto">
                <!-- Left brand area -->
                <div class="flex-1 animate-slide-up" style="animation-delay: 0.1s;">
                    <!-- Logo -->
                    <div class="flex items-center gap-3 mb-8">
                        <div class="relative">
                            <div class="absolute inset-0 bg-gradient-to-r from-primary-500 to-accent-500 blur-lg opacity-50"></div>
                            <img src="../../assets/icon.svg" class="relative w-12 h-12 drop-shadow-lg" alt="Logo">
                        </div>
                        <span class="text-2xl font-bold text-white/90 font-display tracking-tight">PopGenAgent</span>
                    </div>
                    
                    <!-- Main title -->
                    <h1 class="text-5xl md:text-6xl font-extrabold mb-6 leading-tight font-display">
                        <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 via-accent-400 to-cyber-400 animate-gradient-x">
                            Next-Gen
                        </span>
                        <br>
                        <span class="text-white">Population</span>
                        <br>
                        <span class="text-white/80">Genetics Analysis</span>
                    </h1>
                    
                    <!-- Description -->
                    <p class="text-lg text-dark-300 leading-relaxed max-w-lg mb-8">
                        An LLM-driven agent for single-cell data analysis, ensuring high-quality results with minimal effort. 
                        <span class="text-primary-400">Powered by AI.</span>
                    </p>
                    
                    <!-- Feature tags -->
                    <div class="flex flex-wrap gap-3">
                        <div class="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-white/70 backdrop-blur-sm">
                            <span class="inline-block w-2 h-2 rounded-full bg-primary-400 mr-2"></span>
                            ChatAgent
                        </div>
                        <div class="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-white/70 backdrop-blur-sm">
                            <span class="inline-block w-2 h-2 rounded-full bg-accent-400 mr-2"></span>
                            ExecuteAgent
                        </div>
                        <div class="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-white/70 backdrop-blur-sm">
                            <span class="inline-block w-2 h-2 rounded-full bg-cyber-400 mr-2"></span>
                            AnalysisAgent
                        </div>
                    </div>
                </div>

                <!-- Right login form -->
                <div class="w-[420px] animate-slide-up" style="animation-delay: 0.3s;">
                    <div class="relative">
                        <!-- Card glow -->
                        <div class="absolute -inset-1 bg-gradient-to-r from-primary-500/20 via-accent-500/20 to-cyber-500/20 rounded-3xl blur-xl opacity-70"></div>
                        
                        <!-- Login card -->
                        <div class="relative bg-white/[0.03] backdrop-blur-xl rounded-2xl border border-white/10 p-8 shadow-2xl">
                            <!-- Card header -->
                            <div class="text-center mb-8">
                                <h2 class="text-2xl font-bold text-white mb-2 font-display">Welcome Back</h2>
                                <p class="text-dark-400 text-sm">Sign in to continue your research</p>
                            </div>

                            <!-- Login form -->
                            <form class="space-y-5" @submit.prevent="onSubmit">
                                <!-- Email input -->
                                <div class="space-y-2">
                                    <label class="block text-sm font-medium text-white/70 ml-1" for="email">Email</label>
                                    <div class="relative group">
                                        <div class="absolute inset-0 bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-xl opacity-0 group-focus-within:opacity-100 transition-opacity blur-sm"></div>
                                        <input 
                                            type="email" 
                                            id="email"
                                            v-model="email"
                                            class="relative w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-dark-500 focus:outline-none focus:border-primary-500/50 focus:bg-white/[0.07] transition-all duration-300"
                                            placeholder="your@email.com"
                                        >
                                    </div>
                                </div>

                                <!-- Password input -->
                                <div class="space-y-2">
                                    <label class="block text-sm font-medium text-white/70 ml-1" for="password">Password</label>
                                    <div class="relative group">
                                        <div class="absolute inset-0 bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-xl opacity-0 group-focus-within:opacity-100 transition-opacity blur-sm"></div>
                                        <input 
                                            type="password" 
                                            id="password"
                                            v-model="password"
                                            class="relative w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-dark-500 focus:outline-none focus:border-primary-500/50 focus:bg-white/[0.07] transition-all duration-300"
                                            placeholder="••••••••"
                                        >
                                    </div>
                                </div>

                                <!-- Remember me & Register link -->
                                <div class="flex items-center justify-between text-sm">
                                    <label class="flex items-center gap-2 cursor-pointer group">
                                        <div class="relative">
                                            <input type="checkbox" id="remember" class="sr-only peer">
                                            <div class="w-5 h-5 border border-white/20 rounded-md bg-white/5 peer-checked:bg-primary-500 peer-checked:border-primary-500 transition-all"></div>
                                            <svg class="absolute inset-0 w-5 h-5 text-white opacity-0 peer-checked:opacity-100 transition-opacity p-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                                            </svg>
                                        </div>
                                        <span class="text-dark-400 group-hover:text-dark-300 transition-colors">Remember me</span>
                                    </label>
                                    <RouterLink to="/register" class="text-primary-400 hover:text-primary-300 transition-colors font-medium">
                                        Register →
                                    </RouterLink>
                                </div>

                                <!-- Login button -->
                                <button 
                                    type="submit"
                                    class="relative w-full py-3.5 mt-4 group overflow-hidden rounded-xl font-semibold text-white transition-all duration-300"
                                >
                                    <div class="absolute inset-0 bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500 bg-[length:200%_100%] group-hover:animate-gradient-x transition-all"></div>
                                    <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 blur-xl"></div>
                                    <span class="relative flex items-center justify-center gap-2">
                                        Sign In
                                        <svg class="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
                                        </svg>
                                    </span>
                                </button>
                            </form>

                            <!-- Divider -->
                            <div class="relative my-8">
                                <div class="absolute inset-0 flex items-center">
                                    <div class="w-full border-t border-white/10"></div>
                                </div>
                                <div class="relative flex justify-center text-xs">
                                    <span class="px-4 bg-dark-900/50 text-dark-500">or continue with</span>
                                </div>
                            </div>

                            <!-- Social login -->
                            <div class="grid grid-cols-3 gap-3">
                                <button class="flex items-center justify-center py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:border-white/20 transition-all group">
                                    <svg class="w-5 h-5 text-dark-400 group-hover:text-white transition-colors" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                                    </svg>
                                </button>
                                <button class="flex items-center justify-center py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:border-white/20 transition-all group">
                                    <svg class="w-5 h-5 text-dark-400 group-hover:text-white transition-colors" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                    </svg>
                                </button>
                                <button class="flex items-center justify-center py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 hover:border-white/20 transition-all group">
                                    <svg class="w-5 h-5 text-dark-400 group-hover:text-white transition-colors" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom decoration -->
        <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
        
        <!-- Logo watermark -->
        <Logo />
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Logo from '../../components/Logo.vue'
import useUserStore from "@/store/pageStore";
import * as cookie from "@/utils/cookie"

const userStore = useUserStore();
const email = ref('');
const password = ref('');

async function onSubmit(){
    cookie.setLogin("true");
    userStore.token = "true";
}
</script>

<style scoped lang="scss">
/* Custom animations */
.animate-slide-up {
    animation: slideUp 0.8s ease-out forwards;
    opacity: 0;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Gradient animation */
.animate-gradient-x {
    background-size: 200% 100%;
    animation: gradientX 3s ease infinite;
}

@keyframes gradientX {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

/* Input focus effect */
input:focus {
    box-shadow: 0 0 0 2px rgba(59, 127, 251, 0.1);
}

/* Button hover glow effect */
button[type="submit"]:hover {
    box-shadow: 0 10px 40px -10px rgba(59, 127, 251, 0.5);
}
</style>
