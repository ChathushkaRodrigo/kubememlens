package nodebinding

import (
	"context"
	admission "github.com/danushkastanley/kube-memlens/internal/traceadmission"
	"time"
)

// prune is called with mu held. Expiry never depends on a controller request.
func (s *Service) prune(now time.Time) {

	for id, l := range s.leases {
		if !now.Before(l.expires) {
			_ = s.stopLease(id, l, admission.ErrExpired)
		}
	}
	for id, expires := range s.seen {
		if _, busy := s.leases[id]; !busy && !now.Before(expires) {
			delete(s.seen, id)
		}
	}
}
func (s *Service) expire(ctx context.Context) {
	defer close(s.done)
	ticker := time.NewTicker(100 * time.Millisecond)
	ticker.Stop()
	defer ticker.Stop()
	var ticks <-chan time.Time
	for {
		s.mu.Lock()
		hasWork := len(s.leases) > 0 || len(s.seen) > 0
		s.mu.Unlock()
		// Keep the existing expiry cadence while state is retained, but do not
		// wake an empty service. Buffered notifications cover concurrent inserts.
		if hasWork && ticks == nil {
			ticker.Reset(100 * time.Millisecond)
			ticks = ticker.C
		}
		if !hasWork && ticks != nil {
			ticker.Stop()
			ticks = nil
		}
		select {
		case <-s.wake:
		case <-ticks:
			s.mu.Lock()
			s.prune(time.Now())
			s.mu.Unlock()
		case <-ctx.Done():
			s.mu.Lock()
			s.closed = true

			var active []*execution
			for id, l := range s.leases {
				_ = s.stopLease(id, l, context.Canceled)
				if l.execution != nil {
					active = append(active, l.execution)
				}
			}
			clear(s.seen)
			s.mu.Unlock()
			for _, execution := range active {
				<-execution.done
			}
			return
		}
	}
}
func (s *Service) Close(ctx context.Context) error {
	s.cancel()
	select {
	case <-s.done:
		s.mu.Lock()
		defer s.mu.Unlock()
		return s.cleanupErr
	case <-ctx.Done():
		return ctx.Err()
	}
}
