/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  moduleFileExtensions: ['ts', 'js', 'json'],
  testMatch: ['**/*.spec.ts'],
  transform: {
    '^.+\\.ts$': ['ts-jest', { tsconfig: 'tsconfig.spec.json' }],
  },
  transformIgnorePatterns: ['node_modules/(?!@angular)'],
  moduleNameMapper: {
    '^@angular/core$': '<rootDir>/src/__mocks__/angular.ts',
    '^@angular/common/http$': '<rootDir>/src/__mocks__/angular.ts',
  },
  coverageDirectory: 'coverage',
  collectCoverageFrom: ['src/**/*.ts', '!src/main.ts', '!src/**/*.config.ts', '!src/**/*.routes.ts'],
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
  },
};
