<script setup>
import { computed } from 'vue'
import AppIcon from '../common/AppIcon.vue'
import { directionsUrl } from '../../utils/location'
const props = defineProps({ address: { type: String, default: '' } })
const href = computed(() => directionsUrl(props.address))
</script>
<template>
  <a v-if="href" :href="href" target="_blank" rel="noopener noreferrer" class="btn btn--outline btn--sm"
     aria-label="Chỉ đường bằng Google Maps (mở tab mới)">
    <AppIcon name="map-pin" :size="16" />Chỉ đường
  </a>
</template>
