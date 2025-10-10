<script setup lang="ts">
import AppHeader from './components/header/AppHeader.vue'
import HomeBody from './components/body/HomeBody.vue'
import ChatBox from './components/chatbox/ChatBox.vue'
import { ref } from 'vue'

const inputValue = ref('')

const handleSend = () => {
  inputValue.value = ''
}
</script>

<template>
  <div class="mobile-container">
    <AppHeader />

    <main class="home-main">
      <HomeBody />
    </main>

    <ChatBox
      v-model="inputValue"
      @send="handleSend"
    />
  </div>
</template>

<style scoped>
.mobile-container {
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  width: 100vw;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
  background: #ffffff;
  position: relative;
}

.home-main {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.survey-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: #fff;
}

@media screen and (max-width: 480px) {
  .mobile-container {
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    max-width: none;
    margin: 0;
    padding: 0;
  }

  .survey-view {
    margin: 0;
    background: #fff;
  }
}

@media screen and (min-width: 481px) {
  .mobile-container {
    width: 480px;
    max-width: 480px;
    margin: 0 auto;
    height: 100vh;
    height: 100dvh;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
  }
}

@media screen and (orientation: landscape) {
  .mobile-container {
    width: 100vw;
    height: 100vh;
    max-width: 480px;
    margin: 0 auto;
  }

  @media screen and (max-width: 820px) {
    .mobile-container {
      width: 50vh;
      max-width: 480px;
      margin: 0 auto;
    }
  }
}

@media screen and (min-width: 1200px) {
  .mobile-container {
    width: 480px;
    max-width: 480px;
    margin: 0 auto;
    box-shadow: 0 0 30px rgba(0, 0, 0, 0.15);
    border-radius: 0;
  }
}

@media (prefers-color-scheme: dark) {
  .mobile-container {
    background: #000000;
  }

  .survey-view {
    background: #000000;
  }
}
</style>
