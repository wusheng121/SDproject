Component({
  properties: {
    product: {
      type: Object,
      value: {}
    }
  },
  methods: {
    openProduct() {
      this.triggerEvent("open", { id: this.data.product.id });
    }
  }
});
