<script setup>
const roles = [
  { name: 'Shop', description: 'Tạo yêu cầu gửi hàng, theo dõi vận đơn và nhận hàng hoàn.' },
  { name: 'Nhân viên', description: 'Duyệt vận đơn, điều phối shipper và xử lý giao lại, hoàn hàng.' },
  { name: 'Shipper', description: 'Xem nhiệm vụ, lấy hàng, giao hàng và cập nhật kết quả.' },
]
</script>

<template>
  <main class="container">
    <p class="eyebrow">HTT EXPRESS · HÀ NỘI</p>
    <h1>Hệ thống quản lý vận đơn</h1>
    <p class="intro">Bộ khung dự án đã sẵn sàng để phát triển các chức năng nghiệp vụ.</p>
    <section class="roles" aria-label="Vai trò trong hệ thống">
      <article v-for="role in roles" :key="role.name">
        <h2>{{ role.name }}</h2>
        <p>{{ role.description }}</p>
      </article>
    </section>
  </main>
</template>
