<template>
  <div>
    <h1>IceGods Dashboard</h1>
    <section>
      <h2>Wallet Balances</h2>
      <div v-for="(balance, coin) in wallets" :key="coin">
        {{ coin }}: {{ balance }}
      </div>
    </section>

    <section>
      <h2>Subscriptions</h2>
      <ul>
        <li v-for="sub in subscriptions" :key="sub[0]">
          User: {{ sub[1] }} - Plan: {{ sub[2] }} - Amount: ${{ sub[3] }}
        </li>
      </ul>
    </section>

    <section>
      <h2>Sweeps</h2>
      <ul>
        <li v-for="sweep in sweeps" :key="sweep[0]">
          User: {{ sweep[1] }} - Token: {{ sweep[2] }} - Amount: {{ sweep[3] }}
        </li>
      </ul>
    </section>
  </div>
</template>

<script>
import axios from "axios";

export default {
  data() {
    return {
      wallets: {},
      subscriptions: [],
      sweeps: []
    };
  },
  mounted() {
    axios.get("http://localhost:5000/api/wallets").then(res => this.wallets = res.data);
    axios.get("http://localhost:5000/api/subscriptions").then(res => this.subscriptions = res.data);
    axios.get("http://localhost:5000/api/sweeps").then(res => this.sweeps = res.data);
  }
};
</script>
