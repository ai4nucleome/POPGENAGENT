<template>
    <div class="relative w-screen min-h-screen overflow-x-hidden bg-dark-900">
        <!-- Fixed navigation bar -->
        <nav class="fixed top-0 left-0 right-0 z-50 transition-all duration-300" :class="scrolled ? 'bg-dark-900/80 backdrop-blur-xl border-b border-white/10' : ''">
            <div class="max-w-7xl mx-auto px-6 py-4">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3 cursor-pointer group" @click="onSubmit">
                        <div class="relative">
                            <div class="absolute inset-0 bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl blur-lg opacity-0 group-hover:opacity-50 transition-opacity"></div>
                            <img src="../../assets/icon.svg" class="relative w-10 h-10">
                        </div>
                        <span class="text-xl font-bold text-white font-display">PopGenAgent</span>
                    </div>
                    <button 
                        class="px-6 py-2.5 rounded-full bg-gradient-to-r from-primary-500 to-accent-500 text-white font-semibold text-sm hover:shadow-lg hover:shadow-primary-500/30 transition-all hover:scale-105"
                        @click="onSubmit"
                    >
                        Get Started
                    </button>
                </div>
            </div>
        </nav>

        <!-- Hero Section -->
        <section class="relative min-h-screen flex items-center justify-center overflow-hidden">
            <!-- Dynamic background -->
            <div class="absolute inset-0">
                <div class="absolute inset-0 bg-gradient-to-br from-dark-900 via-dark-800 to-dark-900"></div>
                <div class="absolute top-[-20%] left-[-10%] w-[700px] h-[700px] rounded-full bg-primary-500/15 blur-[150px] animate-pulse-slow"></div>
                <div class="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-accent-500/15 blur-[120px] animate-pulse-slow" style="animation-delay: 2s;"></div>
                <div class="absolute top-[40%] right-[20%] w-[400px] h-[400px] rounded-full bg-cyber-500/10 blur-[100px] animate-float"></div>
                
                <!-- Grid background -->
                <div class="absolute inset-0 opacity-[0.03]"
                    style="background-image: linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 60px 60px;">
                </div>
            </div>

            <div class="relative z-10 max-w-6xl mx-auto px-6 pt-24 pb-16 text-center">
                <!-- Badge -->
                <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 mb-8 animate-fade-in">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span class="text-sm text-white/70">AI-Powered Population Genetics</span>
                </div>

                <!-- Main title -->
                <h1 class="text-5xl md:text-7xl font-extrabold mb-6 leading-tight font-display animate-slide-up">
                    <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 via-accent-400 to-cyber-400">
                        PopGenAgent
                    </span>
                </h1>
                <h2 class="text-2xl md:text-3xl text-white/80 mb-6 font-medium animate-slide-up" style="animation-delay: 0.1s;">
                    Advanced Population Genetics Analysis Suite
                </h2>
                <p class="text-lg text-dark-300 max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up" style="animation-delay: 0.2s;">
                    An LLM-driven agent system delivering high-fidelity genomics insights with minimal manual intervention. Ushering in a new era of scientific automation.
                </p>

                <!-- CTA button -->
                <div class="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-slide-up" style="animation-delay: 0.3s;">
                    <button 
                        class="group relative px-8 py-4 rounded-2xl overflow-hidden font-bold text-lg text-white transition-all hover:scale-105"
                        @click="onSubmit"
                    >
                        <div class="absolute inset-0 bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500 bg-[length:200%_100%] animate-gradient-x"></div>
                        <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-r from-primary-400 via-accent-400 to-primary-400 blur-xl"></div>
                        <span class="relative flex items-center gap-2">
                            Try PopGenAgent Now
                            <svg class="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                            </svg>
                        </span>
                    </button>
                    <a href="#features" class="px-8 py-4 rounded-2xl border border-white/20 text-white/80 font-semibold hover:bg-white/5 transition-all">
                        Learn More
                    </a>
        </div>

                <!-- Statistics -->
                <div class="grid grid-cols-3 gap-8 max-w-2xl mx-auto animate-slide-up" style="animation-delay: 0.4s;">
                    <div class="text-center">
                        <div class="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400">107%</div>
                        <div class="text-sm text-dark-400 mt-1">Higher Accuracy</div>
                    </div>
                    <div class="text-center">
                        <div class="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-accent-400 to-cyber-400">3x</div>
                        <div class="text-sm text-dark-400 mt-1">Faster Analysis</div>
                    </div>
                    <div class="text-center">
                        <div class="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyber-400 to-primary-400">0</div>
                        <div class="text-sm text-dark-400 mt-1">Coding Required</div>
                    </div>
                </div>
            </div>

            <!-- Scroll indicator -->
            <div class="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
                <svg class="w-6 h-6 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
                </svg>
            </div>
        </section>

        <!-- Features Section -->
        <section id="features" class="relative py-24 bg-gradient-to-b from-dark-900 to-dark-800">
            <div class="max-w-6xl mx-auto px-6">
                <div class="text-center mb-16">
                    <h2 class="text-3xl md:text-4xl font-bold text-white mb-4 font-display">Powerful Capabilities</h2>
                    <p class="text-lg text-dark-300 max-w-2xl mx-auto">
                        PopGenAgent emulates the analytical acumen of human experts, automating complex genomics workflows
                    </p>
                </div>

                <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div v-for="(feature, index) in features" :key="index" 
                        class="group p-6 rounded-2xl bg-white/[0.03] border border-white/10 hover:border-primary-500/30 hover:bg-white/[0.05] transition-all duration-300">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <component :is="feature.icon" class="w-6 h-6 text-primary-400" />
                        </div>
                        <h3 class="text-lg font-semibold text-white mb-2">{{ feature.title }}</h3>
                        <p class="text-sm text-dark-400 leading-relaxed">{{ feature.description }}</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Comparison Section -->
        <section class="relative py-24 bg-dark-800">
            <div class="max-w-6xl mx-auto px-6">
                <div class="text-center mb-16">
                    <h2 class="text-3xl md:text-4xl font-bold text-white mb-4 font-display">Superior Analysis</h2>
                    <p class="text-lg text-dark-300 max-w-2xl mx-auto">
                        PopGenAgent transcends conventional analysis methods with advanced automation
                    </p>
                </div>

                <div class="grid md:grid-cols-2 gap-8">
                    <!-- Traditional -->
                    <div class="p-8 rounded-2xl bg-white/[0.02] border border-white/10">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="w-10 h-10 rounded-xl bg-dark-600 flex items-center justify-center">
                                <svg class="w-5 h-5 text-dark-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                            </div>
                            <h3 class="text-xl font-semibold text-white">Traditional Analysis</h3>
        </div>
                        <ul class="space-y-3">
                            <li class="flex items-start gap-3 text-dark-400">
                                <span class="w-1.5 h-1.5 rounded-full bg-dark-500 mt-2 shrink-0"></span>
                                Demands programming proficiency
                            </li>
                            <li class="flex items-start gap-3 text-dark-400">
                                <span class="w-1.5 h-1.5 rounded-full bg-dark-500 mt-2 shrink-0"></span>
                                Requires in-depth biological knowledge
                            </li>
                            <li class="flex items-start gap-3 text-dark-400">
                                <span class="w-1.5 h-1.5 rounded-full bg-dark-500 mt-2 shrink-0"></span>
                                Involves manual hyperparameter tuning
                            </li>
                        </ul>
                    </div>

                    <!-- PopGenAgent -->
                    <div class="p-8 rounded-2xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 border border-primary-500/30">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                                </svg>
                            </div>
                            <h3 class="text-xl font-semibold text-white">PopGenAgent</h3>
                        </div>
                        <ul class="space-y-3">
                            <li class="flex items-start gap-3 text-white/80">
                                <span class="w-1.5 h-1.5 rounded-full bg-primary-400 mt-2 shrink-0"></span>
                                Minimizes coding, dialogue-based interactions
                            </li>
                            <li class="flex items-start gap-3 text-white/80">
                                <span class="w-1.5 h-1.5 rounded-full bg-primary-400 mt-2 shrink-0"></span>
                                Collaborates with LLM-driven biological experts
                            </li>
                            <li class="flex items-start gap-3 text-white/80">
                                <span class="w-1.5 h-1.5 rounded-full bg-primary-400 mt-2 shrink-0"></span>
                                Automatically optimizes for enhanced accuracy
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>

        <!-- Performance Section -->
        <section class="relative py-24 bg-gradient-to-b from-dark-800 to-dark-900">
            <div class="max-w-6xl mx-auto px-6">
                <div class="text-center mb-16">
                    <h2 class="text-3xl md:text-4xl font-bold text-white mb-4 font-display">Proven Performance</h2>
                    <p class="text-lg text-dark-300 max-w-2xl mx-auto">
                        PopGenAgent consistently adapts the most appropriate tools and hyperparameters
                    </p>
        </div>

                <div class="grid md:grid-cols-3 gap-8">
                    <div class="text-center p-8 rounded-2xl bg-white/[0.02] border border-white/10">
                        <div class="text-sm text-dark-400 mb-2">GPT-4</div>
                        <div class="text-5xl font-bold text-dark-500 mb-2">47%</div>
                        <div class="text-sm text-dark-500">Task Completion</div>
                    </div>
                    <div class="text-center p-8 rounded-2xl bg-white/[0.02] border border-white/10">
                        <div class="text-sm text-dark-400 mb-2">CellAgent</div>
                        <div class="text-5xl font-bold text-white/60 mb-2">92%</div>
                        <div class="text-sm text-dark-400">Task Completion</div>
                    </div>
                    <div class="text-center p-8 rounded-2xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 border border-primary-500/30">
                        <div class="text-sm text-primary-400 mb-2">PopGenAgent</div>
                        <div class="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400 mb-2">107%</div>
                        <div class="text-sm text-white/70">Superior Performance</div>
                    </div>
                </div>
                </div>
        </section>

        <!-- CTA Section -->
        <section class="relative py-24 bg-dark-900 overflow-hidden">
            <div class="absolute inset-0">
                <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-gradient-to-r from-primary-500/20 via-accent-500/20 to-cyber-500/20 blur-[100px]"></div>
            </div>
            
            <div class="relative max-w-4xl mx-auto px-6 text-center">
                <div class="p-12 rounded-3xl bg-gradient-to-br from-white/[0.05] to-white/[0.02] border border-white/10 backdrop-blur-xl">
                    <h2 class="text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                        Ready to Transform Your Research?
                    </h2>
                    <p class="text-lg text-dark-300 mb-8 max-w-2xl mx-auto">
                        We are excited about the potential of PopGenAgent to significantly enhance productivity, foster new discoveries, and deepen our understanding of biological systems.
                    </p>
                    <button 
                        class="group relative px-10 py-4 rounded-2xl overflow-hidden font-bold text-lg text-white transition-all hover:scale-105"
                        @click="onSubmit"
                    >
                        <div class="absolute inset-0 bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500 bg-[length:200%_100%] animate-gradient-x"></div>
                        <span class="relative flex items-center gap-2">
                            Try PopGenAgent Now
                            <svg class="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
                            </svg>
                        </span>
                        </button>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="py-8 border-t border-white/10">
            <div class="max-w-6xl mx-auto px-6 text-center">
                <p class="text-sm text-dark-500">© 2024 PopGenAgent. All rights reserved.</p>
            </div>
        </footer>
        </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, h } from 'vue';
import * as cookie from "@/utils/cookie"

const scrolled = ref(false);

const features = [
    {
        icon: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' })
        ]),
        title: 'Task Decomposition',
        description: 'Decomposes complex genomics tasks into manageable sub-tasks, executing them sequentially and logically.'
    },
    {
        icon: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M13 10V3L4 14h7v7l9-11h-7z' })
        ]),
        title: 'Automated Execution',
        description: 'Seamlessly automates code generation and execution, delivering captivating plots and insights.'
    },
    {
        icon: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' })
        ]),
        title: 'Self-Optimization',
        description: 'Automatically refines solutions and pinpoints the most optimal one for presentation.'
    },
    {
        icon: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
            h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' })
        ]),
        title: 'Interactive Feedback',
        description: 'Comprehends natural language instructions and responds with tailored code solutions.'
    }
];

function handleScroll() {
    scrolled.value = window.scrollY > 50;
}

onMounted(() => {
    window.addEventListener('scroll', handleScroll);
});

onUnmounted(() => {
    window.removeEventListener('scroll', handleScroll);
});

async function onSubmit() {
    cookie.setLogin("true");
    location.reload();
}
</script>

<style scoped lang="scss">
/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes gradientX {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

@keyframes pulseSlow {
    0%, 100% { opacity: 0.5; transform: scale(1); }
    50% { opacity: 0.8; transform: scale(1.1); }
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-30px); }
}

.animate-fade-in {
    animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
    animation: slideUp 0.8s ease-out forwards;
    opacity: 0;
}

.animate-gradient-x {
    animation: gradientX 3s ease infinite;
}

.animate-pulse-slow {
    animation: pulseSlow 8s ease-in-out infinite;
}

.animate-float {
    animation: float 10s ease-in-out infinite;
}

/* Smooth scroll */
html {
    scroll-behavior: smooth;
}
</style>
