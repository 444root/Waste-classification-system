import { Injectable, NotFoundException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { resolve } from 'node:path';
import { DatabaseService } from '../database/database.service';

interface CountRow {
  count: number;
}

interface FeedbackImageRow {
  image_path: string;
  mime_type: string;
}

@Injectable()
export class AdminService {
  private readonly feedbackDir: string;

  constructor(
    private readonly db: DatabaseService,
    config: ConfigService,
  ) {
    this.feedbackDir = config.get<string>(
      'FEEDBACK_DIR',
      resolve(process.cwd(), 'data', 'feedback'),
    );
  }

  async overview() {
    const [users, classifications, feedback, corrections, userRows, recent, feedbackRows] =
      await Promise.all([
        this.db.query<CountRow>('SELECT COUNT(*)::int AS count FROM users'),
        this.db.query<CountRow>(
          'SELECT COUNT(*)::int AS count FROM classification_history',
        ),
        this.db.query<CountRow>(
          'SELECT COUNT(*)::int AS count FROM classification_feedback',
        ),
        this.db.query<CountRow>(
          `SELECT COUNT(*)::int AS count FROM classification_feedback
           WHERE predicted_category <> corrected_category`,
        ),
        this.db.query(
          `SELECT u.id, u.name, u.email, u.role,
                  u.created_at AS "createdAt",
                  COUNT(h.id)::int AS "classificationCount"
           FROM users u
           LEFT JOIN classification_history h ON h.user_id = u.id
           GROUP BY u.id
           ORDER BY u.created_at DESC`,
        ),
        this.db.query(
          `SELECT h.id, u.name AS "userName", h.original_name AS "originalName",
                  h.predicted_category AS category, h.confidence, h.accepted,
                  h.created_at AS "createdAt"
           FROM classification_history h
           JOIN users u ON u.id = h.user_id
           ORDER BY h.created_at DESC
           LIMIT 30`,
        ),
        this.feedbackList(),
      ]);

    return {
      stats: {
        users: users.rows[0].count,
        classifications: classifications.rows[0].count,
        feedback: feedback.rows[0].count,
        corrections: corrections.rows[0].count,
      },
      users: userRows.rows,
      recentClassifications: recent.rows,
      recentFeedback: feedbackRows.slice(0, 30),
    };
  }

  async feedbackList() {
    const result = await this.db.query(
      `SELECT f.id, u.name AS "userName", f.predicted_category AS "predictedCategory",
              f.corrected_category AS "correctedCategory", f.confidence,
              f.original_name AS "originalName", f.created_at AS "createdAt"
       FROM classification_feedback f
       JOIN users u ON u.id = f.user_id
       ORDER BY f.created_at DESC`,
    );
    return result.rows;
  }

  async feedbackImage(id: string) {
    const result = await this.db.query<FeedbackImageRow>(
      `SELECT image_path, mime_type
       FROM classification_feedback WHERE id = $1 LIMIT 1`,
      [id],
    );
    const item = result.rows[0];
    if (!item) throw new NotFoundException('Feedback image not found');
    return {
      path: resolve(this.feedbackDir, item.image_path),
      mimeType: item.mime_type,
    };
  }
}
