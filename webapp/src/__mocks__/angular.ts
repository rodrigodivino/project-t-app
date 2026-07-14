export function Injectable() {
  return function (_target: any) {};
}

export function Component(_config: any) {
  return function (_target: any) {};
}

export class EventEmitter<T = any> {
  emit(_value?: T) {}
  subscribe(_fn: any) {}
}

export function Output() {
  return function (_target: any, _key: string) {};
}
