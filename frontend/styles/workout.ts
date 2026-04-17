import { StyleSheet } from 'react-native';

export const workoutStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  restContainer: {
    backgroundColor: '#1C1C1E',
  },
  finishedContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#0F0F0F',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  progressText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#888',
    textTransform: 'uppercase',
  },
  progressBarBackground: {
    height: 4,
    backgroundColor: 'rgba(0,0,0,0.1)',
    marginHorizontal: 20,
    borderRadius: 2,
    marginTop: 5,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 2,
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  restCard: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 24,
    padding: 30,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  restTitle: {
    fontSize: 32,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 2,
  },
  restTimer: {
    fontSize: 80,
    fontWeight: '900',
    color: '#4ADE80',
    marginVertical: 10,
    fontVariant: ['tabular-nums'],
  },
  nextBox: {
    marginTop: 20,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 16,
    padding: 20,
    width: '100%',
  },
  nextLabel: {
    color: '#aaa',
    fontSize: 14,
    fontWeight: '600',
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  nextTitle: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '700',
    marginBottom: 8,
  },
  nextDesc: {
    color: '#ccc',
    fontSize: 14,
    lineHeight: 20,
  },
  titleText: {
    fontSize: 32,
    fontWeight: '800',
    color: '#FFF',
    marginTop: 20,
    marginBottom: 10,
  },
  subtitleText: {
    fontSize: 18,
    color: '#A1A1A1',
    marginBottom: 40,
    textAlign: 'center',
  },
  primaryButton: {
    backgroundColor: '#FF5E0E',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 30,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
});
