DO $$
DECLARE demo_product_id INT;
BEGIN
    SELECT product_id INTO demo_product_id
    FROM audited_products
    WHERE title = 'Limited time insulated bottle' AND seller_id = 'demo-seller'
    LIMIT 1;

    IF demo_product_id IS NULL THEN
        INSERT INTO audited_products (title, seller_id, raw_text, status, phase_reached,
                                      review_category, scores_json, audited_at)
        VALUES ('Limited time insulated bottle', 'demo-seller',
                'Hurry, only 2 left! Offer ends tonight.', 'Flagged', 3,
                'deceptive_urgency', '{"deceptive_urgency": 0.96, "safe": 0.02}', CURRENT_TIMESTAMP)
        RETURNING product_id INTO demo_product_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM compliance_flags WHERE product_id = demo_product_id) THEN
        INSERT INTO compliance_flags (product_id, violation_category, confidence_score,
                                      flagged_text_snippet, start_char, end_char, source)
        VALUES (demo_product_id, 'deceptive_urgency', 0.9600,
                'Hurry, only 2 left! Offer ends tonight.', 0, 39, 'demo');
    END IF;
END $$;
